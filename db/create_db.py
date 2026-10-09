"""schema.sql 로 SQLite DB 파일을 만든다.

사용법:  python db/create_db.py [DB경로]   (기본: db/seoul_bicycle.db)
"""
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "seoul_bicycle.db"

with sqlite3.connect(db_path) as conn:
    conn.executescript((HERE / "schema.sql").read_text(encoding="utf-8"))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

print(f"DB 생성 완료: {db_path}")
print("테이블:", ", ".join(tables))
