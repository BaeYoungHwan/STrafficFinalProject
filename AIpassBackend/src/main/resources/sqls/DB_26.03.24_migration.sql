-- ============================================================
-- DB_26.03.24 마이그레이션 (26.03.18 → 26.03.24 + src_image_url)
-- 멱등성 보장: 이미 적용된 환경에서 재실행 가능
-- PostgreSQL 17 기준 (localhost:5432/aipass)
-- ============================================================

-- ① violation_log: intersection_id 컬럼이 존재하는 경우에만 nullable 처리
DO $$ BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'violation_log' AND column_name = 'intersection_id'
  ) THEN
    ALTER TABLE violation_log ALTER COLUMN intersection_id DROP NOT NULL;
    ALTER TABLE violation_log DROP CONSTRAINT IF EXISTS violation_log_intersection_id_fkey;
  END IF;
END $$;

-- ② violation_log: 신규 컬럼 추가
ALTER TABLE violation_log ADD COLUMN IF NOT EXISTS event_id      VARCHAR(100);
ALTER TABLE violation_log ADD COLUMN IF NOT EXISTS speed_kmh     NUMERIC(5,1);
ALTER TABLE violation_log ADD COLUMN IF NOT EXISTS src_image_url VARCHAR(255);

-- ③ event_id UNIQUE 제약조건
DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'violation_log_event_id_key'
  ) THEN
    ALTER TABLE violation_log ADD CONSTRAINT violation_log_event_id_key UNIQUE (event_id);
  END IF;
END $$;

-- ④ sensor_log: motor_current 추가
ALTER TABLE sensor_log ADD COLUMN IF NOT EXISTS motor_current NUMERIC(6,2);

-- ⑤ cctv_info (신규 테이블)
CREATE TABLE IF NOT EXISTS cctv_info (
    cctv_id    VARCHAR(50)  PRIMARY KEY,
    cctv_name  VARCHAR(200) NOT NULL,
    road_name  VARCHAR(200),
    latitude   NUMERIC(10,8),
    longitude  NUMERIC(11,8),
    stream_url VARCHAR(500),
    district   VARCHAR(50),
    is_active  BOOLEAN,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ⑥ its_route (신규 테이블)
CREATE TABLE IF NOT EXISTS its_route (
    route_id     BIGSERIAL   PRIMARY KEY,
    route_no     VARCHAR(10) UNIQUE,
    route_name   VARCHAR(100),
    collect_up   BOOLEAN,
    collect_down BOOLEAN,
    is_active    BOOLEAN,
    memo         VARCHAR(200),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP
);

-- ⑦ its_collect_log (신규 테이블)
CREATE TABLE IF NOT EXISTS its_collect_log (
    log_id        BIGSERIAL  PRIMARY KEY,
    collect_type  VARCHAR(20),
    status        VARCHAR(20),
    total_count   INTEGER,
    new_count     INTEGER,
    error_message TEXT,
    executed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ⑧ traffic_flow_log (신규 테이블)
CREATE TABLE IF NOT EXISTS traffic_flow_log (
    flow_id          BIGSERIAL   PRIMARY KEY,
    link_id          VARCHAR(50),
    road_name        VARCHAR(200),
    speed            NUMERIC(6,2),
    congestion_level VARCHAR(20),
    direction        VARCHAR(10),
    route_no         VARCHAR(10),
    collected_at     TIMESTAMP,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ⑨ weather_log (신규 테이블)
CREATE TABLE IF NOT EXISTS weather_log (
    weather_id         BIGSERIAL PRIMARY KEY,
    intersection_id    BIGINT REFERENCES intersection(intersection_id),
    temperature        NUMERIC(5,2),
    humidity           INTEGER,
    wind_speed         NUMERIC(5,2),
    wind_direction     VARCHAR(10),
    precipitation      NUMERIC(5,2),
    precipitation_type VARCHAR(20),
    sky_condition      VARCHAR(20),
    visibility         INTEGER,
    collected_at       TIMESTAMP,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ⑩ cctv_info: display_url 컬럼 추가 (브라우저 표시용, stream_url은 AI 처리용)
ALTER TABLE cctv_info ADD COLUMN IF NOT EXISTS display_url VARCHAR(500);

-- ⑪ 강화대교 CCTV 초기 데이터
INSERT INTO cctv_info (cctv_id, cctv_name, road_name, stream_url, display_url, is_active)
VALUES (
    'CAM_INTERSECTION_MAIN',
    '강화대교 CCTV',
    '강화대교',
    'http://cctvsec.ktict.co.kr/4700/7IwvywijJon8b57nEHyy/HICmHjDNZlzApokgfyIqcbcfjCcDjc0+oUyzDpNUdp5eYSrojot1rkyuGDsrQD65IaW4PVKsnHrzxPjyGnd8Kc=',
    'http://localhost:8000/api/v1/stream/video',
    true
) ON CONFLICT (cctv_id) DO UPDATE SET
    stream_url  = EXCLUDED.stream_url,
    display_url = EXCLUDED.display_url,
    is_active   = EXCLUDED.is_active;
