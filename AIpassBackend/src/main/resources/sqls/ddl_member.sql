-- member 테이블 생성 (PostgreSQL)
-- 최초 1회 실행 필요

CREATE TABLE IF NOT EXISTS member (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE,
    password    VARCHAR(255) NOT NULL,
    name        VARCHAR(50)  NOT NULL,
    email       VARCHAR(100) NOT NULL,
    phone       VARCHAR(20)  NOT NULL,
    role        VARCHAR(20)  NOT NULL DEFAULT 'ADMIN',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_member_username ON member (username);

-- 기존 테이블에 컬럼 추가 시 (이미 테이블이 있는 경우)
-- ALTER TABLE member ADD COLUMN IF NOT EXISTS email VARCHAR(100) NOT NULL DEFAULT '';
-- ALTER TABLE member ADD COLUMN IF NOT EXISTS phone VARCHAR(20) NOT NULL DEFAULT '';
