-- ============================================================
-- TrafficController DB 연동을 위한 마이그레이션
-- 실행 대상: localhost:5432/aipass (postgres/1234)
-- 실행 방법: psql -h localhost -U postgres -d aipass -f migration_traffic.sql
-- ============================================================

-- 1. intersection 테이블에 신호 제어 컬럼 추가
ALTER TABLE intersection
    ADD COLUMN IF NOT EXISTS status       VARCHAR(20) DEFAULT 'NORMAL',
    ADD COLUMN IF NOT EXISTS green_time   INT         DEFAULT 40,
    ADD COLUMN IF NOT EXISTS yellow_time  INT         DEFAULT 5,
    ADD COLUMN IF NOT EXISTS red_time     INT         DEFAULT 35;

-- 2. 기존 intersection 데이터가 없으면 샘플 데이터 삽입
INSERT INTO intersection (name, latitude, longitude, status, green_time, yellow_time, red_time)
SELECT * FROM (VALUES
    ('세종대로 사거리',  37.57160000, 126.97700000, 'NORMAL',    40, 5, 35),
    ('강남역 교차로',    37.49790000, 127.02760000, 'NORMAL',    35, 5, 40),
    ('서초IC 교차로',    37.48370000, 127.03220000, 'CAUTION',   30, 5, 45),
    ('잠실역 사거리',    37.51330000, 127.10010000, 'NORMAL',    45, 5, 30),
    ('영등포 로터리',    37.51600000, 126.90700000, 'EMERGENCY', 25, 5, 50),
    ('광화문 삼거리',    37.57590000, 126.97690000, 'NORMAL',    38, 5, 37),
    ('여의도 교차로',    37.52190000, 126.92450000, 'CAUTION',   32, 5, 43),
    ('용산역 사거리',    37.52980000, 126.96470000, 'NORMAL',    42, 5, 33)
) AS v(name, latitude, longitude, status, green_time, yellow_time, red_time)
WHERE NOT EXISTS (SELECT 1 FROM intersection LIMIT 1);

-- 3. 기존 행에 status 값이 없으면 DEFAULT 적용
UPDATE intersection SET status = 'NORMAL' WHERE status IS NULL;
