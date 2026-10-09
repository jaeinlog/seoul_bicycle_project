-- 서울 따릉이 프로젝트 DB 스키마 (SQLite)
-- 출처: data_api 노트북의 df_station, 지하철 A~E 단계 산출물
PRAGMA foreign_keys = ON;

-- 따릉이 대여소 (df_station)
CREATE TABLE IF NOT EXISTS bike_station (
    station_id    TEXT PRIMARY KEY,
    station_name  TEXT NOT NULL,
    latitude      REAL,
    longitude     REAL
);

-- [지하철 A-2] 호선별 역 (subway_points)
CREATE TABLE IF NOT EXISTS subway_points (
    subway_id    TEXT PRIMARY KEY,
    subway_name  TEXT NOT NULL,
    line         TEXT,
    lat          REAL NOT NULL,
    lon          REAL NOT NULL,
    name_key     TEXT NOT NULL,   -- 정규화한 역명
    line_key     TEXT NOT NULL,   -- 정규화한 호선
    phys_key     TEXT NOT NULL    -- 물리역 키 (subway_stations.phys_key)
);
CREATE INDEX IF NOT EXISTS idx_subway_points_phys ON subway_points(phys_key);
CREATE INDEX IF NOT EXISTS idx_subway_points_name_line ON subway_points(name_key, line_key);

-- [지하철 A-3] 물리역: 환승역을 하나로 묶은 위치 1곳 1행 (subway_stations)
CREATE TABLE IF NOT EXISTS subway_stations (
    phys_key     TEXT PRIMARY KEY,
    subway_name  TEXT NOT NULL,
    name_key     TEXT NOT NULL,
    lat          REAL NOT NULL,
    lon          REAL NOT NULL,
    lines        TEXT,            -- 예: '2호선, 3호선'
    n_lines      INTEGER,
    subway_ids   TEXT             -- 쉼표 구분 subway_id
);

-- [지하철 B~C] 역별 시간대 승하차 (CardSubwayTime을 긴 형식으로 변환한 결과)
CREATE TABLE IF NOT EXISTS subway_ridership_hourly (
    use_month     TEXT NOT NULL,      -- YYYYMM
    line          TEXT NOT NULL,      -- 원본 호선명
    station       TEXT NOT NULL,      -- 원본 역명
    hour          INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    boardings     INTEGER,            -- 승차 인원
    alightings    INTEGER,            -- 하차 인원
    job_ymd       TEXT,               -- 원본 작업일자
    source_file   TEXT,
    PRIMARY KEY (use_month, line, station, hour)
);

-- [지하철 D] 승하차 데이터 역 <-> 물리역 매칭 (subway_station_match)
CREATE TABLE IF NOT EXISTS subway_station_match (
    ride_line      TEXT NOT NULL,
    ride_station   TEXT NOT NULL,
    name_key       TEXT NOT NULL,
    line_key       TEXT NOT NULL,
    phys_key       TEXT REFERENCES subway_stations(phys_key),  -- NULL = 매칭 실패
    match_method   TEXT,                                       -- '역명+호선' / '역명만'
    PRIMARY KEY (ride_line, ride_station)
);

-- [지하철 E-3] 대여소별 가장 가까운 역 (bike_nearest_subway)
CREATE TABLE IF NOT EXISTS bike_nearest_subway (
    station_id           TEXT PRIMARY KEY REFERENCES bike_station(station_id),
    station_name         TEXT,
    latitude             REAL,
    longitude            REAL,
    nearest_phys_key     TEXT REFERENCES subway_stations(phys_key),
    nearest_subway_name  TEXT,
    nearest_distance_m   REAL
);

-- [지하철 E-4] 반경 500m 안 (대여소, 역) 쌍 — 다대다 (station_subway_link)
CREATE TABLE IF NOT EXISTS station_subway_link (
    station_id       TEXT NOT NULL REFERENCES bike_station(station_id),
    phys_key         TEXT NOT NULL REFERENCES subway_stations(phys_key),
    station_name     TEXT,
    subway_name      TEXT,
    lines            TEXT,
    distance_m       REAL NOT NULL,
    radius_band      TEXT,            -- '0-300m' / '300-500m'
    rank_in_station  INTEGER,
    is_nearest       INTEGER CHECK (is_nearest IN (0, 1)),
    radius_m         INTEGER,
    PRIMARY KEY (station_id, phys_key)
);
CREATE INDEX IF NOT EXISTS idx_link_phys ON station_subway_link(phys_key);
