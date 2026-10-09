"""API 원본(parquet)을 PostgreSQL 원본 테이블에 그대로 적재한다.

노트북의 '지하철 A-1', '지하철 B' 단계가 저장한 파일이 대상이다.
  subway_station_master_raw  <- subway_station_master_raw.parquet   (subwayStationMaster)
  subway_card_time_raw       <- subway_time_YYYYMM.parquet 여러 개   (CardSubwayTime)

- 원본 보존: 모든 컬럼을 TEXT 로 저장 (노트북도 astype("string") 으로 저장함)
- 컬럼은 parquet 에서 읽어 만들므로 API 컬럼명을 몰라도 되고, 달마다 컬럼이 늘어나면 자동 추가
- 파일 단위로 지우고 다시 넣으므로 중간에 끊겨도 다시 실행하면 이어서 적재됨
- 파일마다 새 연결 + keepalive 사용 (장시간 유휴로 연결이 끊기는 문제 방지)

사용법 (Colab):
    DATABASE_URL 환경변수에 접속 문자열을 넣고
    !python create_raw_tables.py <SUBWAY_RAW_DIR>
"""
import glob
import io
import os
import sys

import psycopg2
import pyarrow.parquet as pq
from psycopg2 import sql

# 테이블명 -> 적재할 parquet 파일 패턴
RAW_TABLES = {
    "subway_station_master_raw": "subway_station_master_raw.parquet",
    "subway_card_time_raw": "subway_time_*.parquet",
    # 따릉이 대여이력 등을 추가할 때는 여기에 한 줄 더하면 된다.
}


def connect():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        keepalives=1, keepalives_idle=30,
        keepalives_interval=10, keepalives_count=5,
        connect_timeout=15,
    )


def ensure_table(cur, table, columns):
    """테이블이 없으면 만들고, 새 컬럼이 있으면 추가한다."""
    cur.execute(sql.SQL(
        "CREATE TABLE IF NOT EXISTS {} ("
        " raw_id BIGSERIAL PRIMARY KEY,"
        " source_file TEXT NOT NULL,"
        " loaded_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    ).format(sql.Identifier(table)))
    cur.execute(sql.SQL(
        "CREATE INDEX IF NOT EXISTS {} ON {} (source_file)"
    ).format(sql.Identifier(f"idx_{table}_source_file"), sql.Identifier(table)))
    for col in columns:
        cur.execute(sql.SQL(
            "ALTER TABLE {} ADD COLUMN IF NOT EXISTS {} TEXT"
        ).format(sql.Identifier(table), sql.Identifier(col)))


def load_file(table, path):
    name = os.path.basename(path)
    df = pq.read_table(path).to_pandas().astype("string")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df.insert(0, "source_file", name)

    conn = connect()
    try:
        with conn.cursor() as cur:
            ensure_table(cur, table, [c for c in df.columns if c != "source_file"])
            cur.execute(sql.SQL("DELETE FROM {} WHERE source_file = %s")
                        .format(sql.Identifier(table)), (name,))
            buf = io.StringIO()
            df.to_csv(buf, index=False, header=False)   # 결측은 빈 값 -> NULL
            buf.seek(0)
            cols = sql.SQL(", ").join(sql.Identifier(c) for c in df.columns)
            cur.copy_expert(
                sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv)")
                .format(sql.Identifier(table), cols).as_string(conn), buf)
        conn.commit()
    except Exception:
        if not conn.closed:
            conn.rollback()
        raise
    finally:
        conn.close()
    print(f"  {name}: {len(df):,}행 적재")


def main(raw_dir):
    for table, pattern in RAW_TABLES.items():
        files = sorted(glob.glob(os.path.join(raw_dir, pattern)))
        print(f"[{table}] 파일 {len(files)}개")
        for path in files:
            load_file(table, path)


if __name__ == "__main__":
    main(sys.argv[1])
