-- =========================================================================
-- 1. 교차로 테이블 (intersection)
-- [역할] 스마트 교차로 시스템의 중심 뼈대. 모든 이벤트(단속, 고장 등)의 '발생 위치(주소)'를 제공함.
-- [관계] 이 시스템의 최상위 부모 테이블. 다른 모든 테이블이 이 테이블의 ID를 참조함.
-- =========================================================================
CREATE TABLE intersection (
    intersection_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
/*
[컬럼 세부 설명 및 코드 의미]
- intersection_id (BIGSERIAL PRIMARY KEY)
  : 교차로 고유 식별자. 
  * BIGSERIAL: 데이터가 추가될 때마다 1, 2, 3... 자동으로 1씩 증가하는 숫자형 타입임.
  * PRIMARY KEY: 중복될 수 없는 테이블의 핵심 키워드(주민번호 같은 역할)임을 선언함.
  
- name (VARCHAR(100) NOT NULL)
  : 교차로 이름 (예: "강남역 사거리"). 
  * NOT NULL: 빈값(Null)으로 둘 수 없는 필수 데이터임을 뜻함.
  
- latitude / longitude (DECIMAL)
  : Vue.js 관제 대시보드 맵에 핀을 꽂기 위한 GPS 좌표임.
  * DECIMAL(10,8): 총 10자리 숫자 중 소수점 아래 8자리까지 정밀하게 저장한다는 뜻임.

- created_at (TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
  : 교차로 데이터 최초 등록 시간.
  * DEFAULT CURRENT_TIMESTAMP: 값을 안 넣어도 DB가 알아서 '현재 시간'을 찍어줌.
*/


-- =========================================================================
-- 2. 단속 장비 테이블 (equipment)
-- [역할] 교차로에 설치된 기기(카메라 모터, 냉각팬 등)들의 호적등본(목록)임.
-- [관계] intersection 테이블과 [1:N] 관계. (교차로 1개에 장비 여러 대 설치됨)
-- =========================================================================
CREATE TABLE equipment (
    equipment_id BIGSERIAL PRIMARY KEY,
    intersection_id BIGINT NOT NULL,
    equipment_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'NORMAL',
    installation_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (intersection_id) REFERENCES intersection(intersection_id)
);
/*
[컬럼 세부 설명 및 코드 의미]
- equipment_id: 단속 장비 고유 번호.

- intersection_id (BIGINT NOT NULL)
  : 이 장비가 소속된 교차로 번호. 

- equipment_type: 장비 종류 (예: 'PTZ_MOTOR', 'COOLING_FAN').

- status (DEFAULT 'NORMAL')
  : 장비 현재 상태. 기본값은 'NORMAL(정상)'이며, 추후 예지보전 AI가 이 값을 'WARNING' 등으로 변경함.

- installation_date (DATE): 장비 설치 일자 (시간 제외, 날짜만 저장함).

[관계(제약 조건) 설명]
- FOREIGN KEY (...) REFERENCES ...
  : 외래키 설정. 
  이 장비는 반드시 'intersection 테이블에 실제로 존재하는 교차로'에만 매달릴 수 있도록 강력하게 연결(제한)함.
*/


-- =========================================================================
-- 3. 위반 차량 적발 내역 테이블 (violation_log)
-- [역할] YOLOv8과 PaddleOCR이 잡아낸 불법 차량 단속 기록장임.
-- [관계] intersection 테이블과 [1:N] 관계. (교차로 1곳에서 위반 내역 무한대 생성됨)
-- =========================================================================
CREATE TABLE violation_log (
    violation_id BIGSERIAL PRIMARY KEY,
    intersection_id BIGINT NOT NULL,
    plate_number VARCHAR(50),
    violation_type VARCHAR(50) NOT NULL,
    image_url VARCHAR(255),
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (intersection_id) REFERENCES intersection(intersection_id)
);
/*
[컬럼 세부 설명 및 코드 의미]
- violation_id: 적발 건수 고유 번호 (딱지 번호).

- intersection_id: 위반 사건이 발생한 교차로 번호.

- plate_number: PaddleOCR이 추출한 번호판 텍스트 (예: "12가 3456").

- violation_type: 위반 종류 (예: 'SPEEDING', 'RED_LIGHT').

- image_url (VARCHAR(255))
  : 증거 사진이 저장된 '경로(웹 주소)'만 텍스트로 저장함. 
  DB에 직접 사진(바이너리)을 넣으면 터지기 때문에 분리 보관하는 것이 핵심임.

- detected_at: 실제 AI가 적발한 시간.
*/

-- =========================================================================
-- [수정] 3. 위반 차량 적발 내역 테이블 (violation_log) 컬럼 추가
-- [역할] 관리자의 과태료 부과 승인 및 번호판 수동 수정/반려 내역을 관리하기 위함.
-- =========================================================================
ALTER TABLE violation_log ADD COLUMN fine_status VARCHAR(20) DEFAULT 'UNPROCESSED';
ALTER TABLE violation_log ADD COLUMN is_corrected BOOLEAN DEFAULT FALSE;

/*
[추가된 컬럼 세부 설명 및 코드 의미]
- fine_status (VARCHAR(20) DEFAULT 'UNPROCESSED')
  : 관리자의 과태료 처리 상태를 저장함.
  * 기본값은 'UNPROCESSED(미처리)'이며, 관리자 화면에서 버튼 클릭 시 'APPROVED(승인/부과)','REJECTED(반려)' 등으로 변경됨.

- is_corrected (BOOLEAN DEFAULT FALSE)
  : AI가 인식한 번호판(plate_number)을 관리자가 수동으로 수정했는지 여부를 기록함.
  * 수정 전은 FALSE(거짓)이며, 관리자가 직접 타이핑하여 수정하면 TRUE(참)로 값이 바뀜.
*/

-- =========================================================================
-- 4. 예지보전 센서 데이터 테이블 (sensor_log)
-- [역할] 기기 예지보전을 위해 1초/1분 단위로 쏟아지는 센서(진동, 온도) 기록 일지임.
-- [관계] equipment 테이블과 [1:N] 관계. (장비 1대에서 센서 로그 무한대 생성됨)
-- =========================================================================
CREATE TABLE sensor_log (
    log_id BIGSERIAL PRIMARY KEY,
    equipment_id BIGINT NOT NULL,
    temperature DECIMAL(6,2),
    vibration DECIMAL(6,2),
    risk_score DECIMAL(3,2),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
);
/*
[컬럼 세부 설명 및 코드 의미]
- log_id: 센서 기록 고유 번호.

- equipment_id: 이 센서값이 측정된 장비의 번호. (교차로가 아니라 '장비'에 직접 연결됨)

- temperature / vibration (DECIMAL(6,2))
  : 온도와 진동 데이터. 소수점 아래 2자리까지만 저장함 (예: 36.52).

- risk_score (DECIMAL(3,2))
  : 머신러닝 AI가 위 온도/진동을 보고 계산한 고장 위험도 (0.00 ~ 1.00 사이의 값). 
  프론트엔드 경고 알림의 핵심 지표임.

- recorded_at: 센서 측정 시간. Vue.js 대시보드의 꺾은선형 차트를 그릴 때 x축(시간)으로 활용함.
*/


-- =========================================================================
-- 5. 혼잡도 통계 테이블 (traffic_congestion)
-- [역할] 시간대별 교차로 차량 통행량과 혼잡 상태를 저장하는 통계 테이블임.
-- [관계] intersection 테이블과 [1:N] 관계.
-- =========================================================================
CREATE TABLE traffic_congestion (
    congestion_id BIGSERIAL PRIMARY KEY,
    intersection_id BIGINT NOT NULL,
    vehicle_count INT DEFAULT 0,
    congestion_level VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (intersection_id) REFERENCES intersection(intersection_id)
);
/*
[컬럼 세부 설명 및 코드 의미]
- congestion_id: 통계 기록 고유 번호.

- intersection_id: 혼잡도를 집계한 교차로 번호.

- vehicle_count (INT)
  : 특정 시간 동안 YOLO가 카운팅한 총 차량 대수 (정수형).

- congestion_level 
  : 혼잡도를 텍스트로 요약함 ('SMOOTH', 'MODERATE', 'HEAVY'). 
  관제 맵 교차로 핀(마커)의 초록/노랑/빨강 색상을 결정하는 기준값임.

- recorded_at: 집계된 시간. 시간대별/일자별 통계를 낼 때 기준이 됨.
*/

-- =========================================================================
-- 6. 회원 정보 테이블 (member)
-- [역할] 시스템에 접속하는 일반 사용자 및 관리자의 계정 정보를 저장함.
-- [관계] 현재는 독립적인 테이블임. (추후 위반 내역 등과 연결될 수 있음)
-- =========================================================================
CREATE TABLE member (
    member_id BIGSERIAL PRIMARY KEY,
    login_id VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE member 
ADD COLUMN email VARCHAR(255) UNIQUE NOT NULL;
/*
[컬럼 세부 설명 및 코드 의미]
- member_id (BIGSERIAL PRIMARY KEY)
  : 회원 고유 식별 번호 (1번 회원, 2번 회원...).

- login_id (VARCHAR(50) UNIQUE NOT NULL)
  : 로그인할 때 사용하는 아이디 (또는 이메일).
  * UNIQUE: 다른 사람과 중복된 아이디를 만들 수 없도록 강력하게 막아줌.

- password (VARCHAR(255) NOT NULL)
  : 로그인 비밀번호. 
  * 비밀번호는 백엔드(Spring Boot)에서 암호화(해싱)되어 아주 긴 알 수 없는 문자열로 저장되기 때문에, 
  넉넉하게 255자로 공간을 잡아둠. 원본 비밀번호를 그대로 DB에 저장하면 절대 안 됨.

- name (VARCHAR(50) NOT NULL)
  : 사용자의 실제 이름 또는 닉네임.

- created_at: 회원가입이 완료된 시간.
*/

-- =========================================================================
-- 7. 신호 제어 이력 테이블 (signal_control_log)
-- [역할] 구급차 등 긴급 차량 진입에 의한 자동 신호 제어 또는 관리자의 수동 제어 내역을 기록함.
-- [관계] intersection 테이블과 [1:N] 관계. (교차로 1곳에서 제어 이벤트 여러 번 발생)
-- =========================================================================
CREATE TABLE signal_control_log (
    control_id BIGSERIAL PRIMARY KEY,
    intersection_id BIGINT NOT NULL,
    control_type VARCHAR(50) NOT NULL,
    control_reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (intersection_id) REFERENCES intersection(intersection_id)
);

/*
[컬럼 세부 설명 및 코드 의미]
- control_id: 신호 제어 기록의 고유 번호.

- intersection_id: 신호 제어가 발생한 교차로 번호.

- control_type (VARCHAR(50) NOT NULL)
  : 제어 방식 (예: 'AUTO_EMERGENCY'(긴급차량 자동제어), 'MANUAL'(관리자 수동제어)).

- control_reason (VARCHAR(255))
  : 신호를 강제로 제어한 구체적인 사유 (예: "구급차 북측 진입으로 인한 강제 녹색불 전환").

- created_at: 제어 이벤트가 발생한 정확한 시간. 제어 내역 팝업창을 띄울 때 기준이 됨.
*/

-- =========================================================================
-- 8. 유지보수 및 수리 티켓 테이블 (maintenance_log)
-- [역할] 예지보전 AI의 고장 위험 알림을 본 관리자가 '기사 호출'을 눌렀을 때 생성되는 작업 지시서(티켓)임.
-- [관계] equipment 테이블과 [1:N] 관계. (장비 1대에 여러 번의 수리 내역이 쌓일 수 있음)
-- =========================================================================
CREATE TABLE maintenance_log (
    ticket_id BIGSERIAL PRIMARY KEY,
    equipment_id BIGINT NOT NULL,
    repair_status VARCHAR(20) DEFAULT 'REQUESTED',
    reported_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
);

/*
[컬럼 세부 설명 및 코드 의미]
- ticket_id: 수리 접수 내역의 고유 번호 (작업 티켓 번호).

- equipment_id: 수리가 필요한 고장(위험) 장비 번호. 센서 테이블이 아닌 장비 테이블과 직접 연결됨.

- repair_status (VARCHAR(20) DEFAULT 'REQUESTED')
  : 현재 수리 진행 상태. 
  * 처음 호출 버튼을 누르면 'REQUESTED(접수완료)', 진행 중일 땐 'IN_PROGRESS(수리중)', 완료되면 'COMPLETED(수리완료)'로 대시보드 화면에 노출됨.

- reported_by (VARCHAR(50))
  : 수리를 요청한 관리자의 이름 또는 ID를 기록함 (누가 호출했는지 책임 소재 명확화).

- created_at: 수리 기사를 호출한(버튼을 누른) 시간.

- resolved_at (TIMESTAMP)
  : 수리가 최종 완료된 시간. 초기엔 빈값(Null)으로 두었다가 수리 완료 시 시간이 기록됨.
*/


/*
=============================================================================
[스마트 교차로 관제 시스템 DB 아키텍처 및 화면 연동 총정리]
=============================================================================

🗺️ 1. 전체 테이블 연결 관계 및 핵심 아키텍처

- 중앙 통제 센터 (1개): intersection (교차로)
  * 모든 테이블은 결국 "이 일이 어느 사거리에서 일어났는가?"를 찾기 위해 이 테이블로 꼬리를 물고 올라오게 됨.

- 교차로에서 파생되는 3대 액션 (자식 테이블):
  * 감시: violation_log (과속/신호위반 찰칵)
  * 통계: traffic_congestion (지금 차가 몇 대 지나가는지 카운팅)
  * 제어: signal_control_log (구급차가 와서 신호를 바꿨는지 기록)

- 장비 관리 전용 파이프라인 (손자 테이블 포함):
  * 교차로에 매달린 equipment(기계 목록) ➔ 그 기계의 건강 상태인 sensor_log(온도/진동) ➔ 아프면 고치는 maintenance_log(수리 티켓) 순서로 흐름이 이어짐.


🖥️ 2. 화면별 데이터 연동 가이드 (어떤 화면에 어떤 데이터가 쓰이는가?)

① 관리자 메인 홈 (요약 대시보드)
  - KPI & 실시간 이벤트 알림:
    * traffic_congestion을 조회해 '오늘 누적 차량 통행량'을 계산함.
    * violation_log를 조회해 '오늘의 과태료 적발 건수'를 띄움.
    * signal_control_log를 조회해 '10:42 AM 구급차 진입 신호 강제 제어' 같은 알림 텍스트를 렌더링함.

② 교통/신호 제어 맵 (2D 지도)
  - 지도 UI 렌더링: intersection의 위도(latitude), 경도(longitude) 데이터를 가져와 지도 위에 핀(마커)을 꽂음.
  - 도로 혼잡도 색상 표시: traffic_congestion의 congestion_level을 읽어서 핀 색깔을 초록/빨강으로 바꿈.
  - 구급차 진입 팝업: AI가 구급차를 감지하면 signal_control_log에 제어 내역을 INSERT하고, 화면에 팝업을 띄움.

③ 단속 내역 관리 화면
  - 위반 차량 리스트 노출: violation_log 데이터를 표(그리드) 형태로 쫙 뿌려줌.
  - 과태료 부과 및 번호판 수정: 관리자가 화면에서 [승인] 버튼이나 [수정] 버튼을 누르면, 
  백엔드에서 violation_log의 fine_status(처리 상태)와 is_corrected(수정 여부) 값을 UPDATE 함.

④ 실비 예지보전 화면
  - 기기 상태 조회: equipment 테이블을 불러와 카메라와 제어기 목록을 띄움.
  - 고장 위험도 차트: sensor_log의 risk_score와 recorded_at을 가져와 실시간 꺾은선 차트(Chart.js)를 그림.
  - 수리 기사 호출: 관리자가 [호출] 버튼을 누르면 maintenance_log에 수리 접수 내역이 INSERT 됨.

⑤ 통계 및 리포트 화면
  - 시간대별 차트: traffic_congestion과 violation_log의 데이터를 recorded_at(시간) 기준으로 
  그룹화(GROUP BY)하여 엑셀이나 차트용 데이터로 제공함.


📝 3. 8개 테이블 기능 및 필요성 최종 요약

- intersection (교차로): 모든 사건의 '주소(위치)'를 담당. 지도 시각화의 필수 데이터임.
- equipment (단속 장비): 어떤 기계가 어디에 설치되어 있는지 관리하는 호적등본임.
- violation_log (단속 내역): AI가 찍은 불법 차량 정보와 관리자의 과태료 승인 업무를 기록함.
- sensor_log (센서 데이터): 예지보전 AI가 기계의 진동/온도를 보고 평가한 '고장 위험도 점수'를 1초마다 기록함.
- traffic_congestion (혼잡도 통계): 도로가 얼마나 막히는지 차량 대수를 기록하여 통계와 지도 색상을 결정함.
- signal_control_log (신호 제어 이력): 구급차 통과나 수동 조작으로 인해 신호등이 언제, 왜 바뀌었는지 감사(Audit)하기 위해 기록함.
- maintenance_log (수리 티켓): 위험 알림을 본 관리자가 수리기사를 부르고, 그 수리가 완료될 때까지의 과정을 추적함.
- member (회원 정보): 이 통합 관제 시스템에 로그인할 수 있는 관리자 전용 계정(아이디, 비밀번호 등)을 관리함.
=============================================================================
*/


CREATE TABLE weather_log (
    weather_id         BIGSERIAL    PRIMARY KEY,
    intersection_id    BIGINT       NOT NULL,
    temperature        DECIMAL(5,2),
    humidity           INT,
    wind_speed         DECIMAL(5,2),
    wind_direction     VARCHAR(10),
    precipitation      DECIMAL(5,2),
    precipitation_type VARCHAR(20),
    sky_condition      VARCHAR(20),
    visibility         INT,
    nx                 INT,
    ny                 INT,
    forecast_time      TIMESTAMP,
    collected_at       TIMESTAMP    NOT NULL,
    created_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (intersection_id) REFERENCES intersection(intersection_id),
    CONSTRAINT uq_weather_intersection_forecast
        UNIQUE (intersection_id, forecast_time)
);

/*
최종 DDL (확정본)

-- =========================================================================
-- weather_log — 기상청 초단기실황 수집 이력
--
-- 수집 주기: 1시간 1회 (매시 05분 실행, 1시간 전 정시 데이터 요청)
-- 수집 기준: intersection 테이블의 교차로 좌표 → 기상청 격자(nx, ny) 변환
-- API: 기상청 초단기실황조회 (getUltraSrtNcst)
--
-- 활용처:
--   1) 예지보전 ML 모델 — temperature를 ambient_temp 입력값으로 사용
--   2) 대시보드 날씨 위젯 — 최신 1건 조회
--   3) 교통 혼잡도 분석 — 기상 조건별 혼잡도 상관관계
--
-- 중복 방지:
--   UNIQUE (intersection_id, forecast_time) + INSERT ON CONFLICT DO NOTHING
--   affected row count로 실제 저장 건수만 카운트
--
-- feels_like 컬럼 미포함 사유:
--   초단기실황 API에 체감온도 카테고리 없음 (항상 NULL)
--   필요 시 서비스 레이어에서 계산식으로 도출
-- =========================================================================

CREATE TABLE weather_log (
    weather_id         BIGSERIAL    PRIMARY KEY,

    -- 교차로 기준 수집 (intersection FK)
    intersection_id    BIGINT       NOT NULL,

    -- 기상 데이터 (API 카테고리 코드 → 변환 후 저장)
    temperature        DECIMAL(5,2),                   -- T1H: 기온 (°C) → ML ambient_temp
    humidity           INT,                            -- REH: 습도 (%)
    wind_speed         DECIMAL(5,2),                   -- WSD: 풍속 (m/s)
    wind_direction     VARCHAR(10),                    -- VEC → 16방위 변환 (N/NNE/NE/...)
    precipitation      DECIMAL(5,2),                   -- RN1: 1시간 강수량 (mm), "강수없음"/"0" → 0.00
    precipitation_type VARCHAR(20),                    -- PTY → NONE / RAIN / SNOW / SLEET
    sky_condition      VARCHAR(20),                    -- SKY → CLEAR / CLOUDY / OVERCAST
    visibility         INT,                            -- VIS × 10: 시정 (m), 음수 → NULL 처리

    -- 기상청 격자 좌표 (위경도 → Lambert Conformal Conic 변환)
    nx                 INT,
    ny                 INT,

    -- 시간 필드
    forecast_time      TIMESTAMP    NOT NULL,          -- API 응답의 baseDate+baseTime (발표 기준 시각)
    collected_at       TIMESTAMP    NOT NULL,          -- 실제 수집 시각 (LocalDateTime.now())
    created_at         TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    -- 제약 조건
    FOREIGN KEY (intersection_id) REFERENCES intersection(intersection_id),
    CONSTRAINT uq_weather_intersection_forecast
        UNIQUE (intersection_id, forecast_time)
        -- 같은 교차로 + 같은 발표 시각 중복 INSERT 방지
        -- 코드: ON CONFLICT (intersection_id, forecast_time) DO NOTHING
);

-- 시계열 조회 인덱스 (대시보드 차트, ML 피처 조인용)
-- intersection_id가 선두 컬럼 → FK 조회도 커버 (별도 FK 인덱스 불필요)
CREATE INDEX idx_weather_log_intersection_time
    ON weather_log (intersection_id, collected_at DESC);

-- 전체 시간순 조회 (운영 모니터링, 일괄 조회용)
CREATE INDEX idx_weather_log_collected_at
    ON weather_log (collected_at DESC);

COMMENT ON TABLE  weather_log                      IS '기상청 초단기실황 1시간 주기 수집 이력';
COMMENT ON COLUMN weather_log.temperature          IS '기온(°C) — 예지보전 ML 모델 ambient_temp 입력값';
COMMENT ON COLUMN weather_log.precipitation_type   IS 'NONE: 없음 / RAIN: 비 / SNOW: 눈 / SLEET: 진눈깨비';
COMMENT ON COLUMN weather_log.sky_condition        IS 'CLEAR: 맑음 / CLOUDY: 구름많음 / OVERCAST: 흐림';
COMMENT ON COLUMN weather_log.visibility           IS '시정(m) — 100 이하: 짙은 안개, 교통 위험 알림용';
COMMENT ON COLUMN weather_log.nx                   IS '기상청 격자 X — 위경도→격자 변환 후 저장';
COMMENT ON COLUMN weather_log.ny                   IS '기상청 격자 Y — 위경도→격자 변환 후 저장';
COMMENT ON COLUMN weather_log.forecast_time        IS '기상청 발표 기준 시각 — API 응답 baseDate+baseTime';
COMMENT ON COLUMN weather_log.collected_at         IS '실제 수집 시각 — 스케줄러/수동 트리거 실행 시점';


-- =========================================================================
-- its_collect_log — 스케줄러 수집 실행 이력
--
-- 용도: 스케줄러(WEATHER/CCTV_INFO/TRAFFIC_FLOW)의 실행 결과 기록
-- 활용처: 운영 모니터링, 장애 추적, 수집 통계
--
-- collect_type 값:
--   WEATHER      — 기상청 날씨 수집 (1시간)
--   CCTV_INFO    — ITS CCTV 정보 수집 (1시간)
--   TRAFFIC_FLOW — ITS 교통소통정보 수집 (5분)
--
-- total_count vs new_count:
--   total_count = 수집 시도 건수
--   new_count   = 실제 DB 저장 건수 (ON CONFLICT 시 차이 발생)
--   현재 코드에서는 affected row 기반으로 동일값 사용
-- =========================================================================

CREATE TABLE its_collect_log (
    log_id        BIGSERIAL    PRIMARY KEY,

    -- 수집 유형 및 결과
    collect_type  VARCHAR(20)  NOT NULL,               -- WEATHER / CCTV_INFO / TRAFFIC_FLOW
    status        VARCHAR(20)  NOT NULL,               -- SUCCESS / FAIL
    total_count   INT          DEFAULT 0,              -- 수집 시도 건수
    new_count     INT          DEFAULT 0,              -- 실제 저장 건수
    error_message TEXT,                                -- 실패 시 예외 메시지

    -- 실행 시각 (DB DEFAULT — 코드에서 별도 세팅 불필요)
    executed_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE  its_collect_log               IS '스케줄러 수집 실행 이력 — 운영 모니터링용';
COMMENT ON COLUMN its_collect_log.collect_type  IS 'WEATHER / CCTV_INFO / TRAFFIC_FLOW';
COMMENT ON COLUMN its_collect_log.status        IS 'SUCCESS: 정상 / FAIL: 실패';
COMMENT ON COLUMN its_collect_log.total_count   IS '수집 시도 건수';
COMMENT ON COLUMN its_collect_log.new_count     IS '실제 DB 저장 건수 (중복 제외)';
COMMENT ON COLUMN its_collect_log.error_message IS '실패 시 예외 메시지 전문';
COMMENT ON COLUMN its_collect_log.executed_at   IS '스케줄러 실행 시각';
선행 확인 사항
이 DDL을 실행하기 전에 아래 2가지가 DB에 존재해야 합니다.

1. intersection 테이블
weather_log의 FK 대상입니다. 최소한 아래 컬럼이 필요합니다:


-- 이미 존재하는 테이블 — 아래 컬럼 확인만 필요
-- intersection_id  BIGINT PRIMARY KEY
-- latitude         DECIMAL(10,7)   ← 격자 변환에 사용
-- longitude        DECIMAL(10,7)   ← 격자 변환에 사용
2. its_collect_log 중복 생성 주의
ITS 교통소통 파트에서 먼저 이 테이블을 만들었다면 CREATE 중복 에러가 납니다. 그 경우 CREATE TABLE IF NOT EXISTS로 변경하거나, 이미 있는 테이블을 그대로 사용하면 됩니다.
*/
  ALTER TABLE violation_log       
  ADD COLUMN IF NOT EXISTS event_id  VARCHAR(100) UNIQUE,
  ADD COLUMN IF NOT EXISTS speed_kmh DECIMAL(5,1);     


  ALTER TABLE violation_log ALTER COLUMN intersection_id DROP NOT NULL; 

  INSERT INTO member (login_id, password, name, email, created_at)                                                                                                                                       
  VALUES (                                                                                                                                                                                                    
	 'admin',                                                                                                                                                                                           
      '$2b$10$lLkoMv7mHMskNF64/0mP0.nIGSnJKlsZurgcwTiBz2y5qCOyMmEl2',                                                                                                                                    
      '관리자',                                                                                                                                                                                          
      'admin@aipass.com',                                                                                                                                                                                
      NOW()                    );   



-----------------------------------------------------------------------

  SELECT column_name, data_type, is_nullable                                                                                                                                                             
  FROM information_schema.columns
  WHERE table_name = 'member'                                                                                                                                                                            
  ORDER BY ordinal_position;      

 UPDATE member                                                                                                                                                                                          
  SET password = 'Qwer123$'                                                                                                                                                       
  WHERE login_id = 'admin';   
	

  select * from member;

-- =========================================================================
-- violation_log 번호판 이미지 경로 컬럼 추가
-- image_url: OCR 후 크롭된 번호판 이미지 상대경로 (예: numberplate/12가3456.jpg)
-- =========================================================================
ALTER TABLE violation_log
  ADD COLUMN IF NOT EXISTS image_url VARCHAR(255);


-- =========================================================================
-- [최종 확정] violation_log 컬럼 보강 — 안전 적용 (IF NOT EXISTS)
-- 과속 감지 파이프라인에 필요한 모든 컬럼을 일괄 추가한다.
-- 실 DB에 이미 적용됐다면 IF NOT EXISTS로 무시되므로 재실행 안전.
-- =========================================================================
ALTER TABLE violation_log
  ADD COLUMN IF NOT EXISTS fine_status  VARCHAR(20) DEFAULT 'UNPROCESSED',
  ADD COLUMN IF NOT EXISTS is_corrected BOOLEAN     DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS event_id     VARCHAR(100),
  ADD COLUMN IF NOT EXISTS speed_kmh    NUMERIC(5,1),
  ADD COLUMN IF NOT EXISTS image_url    VARCHAR(255);

-- event_id UNIQUE 인덱스 (중복 단속 이벤트 방지 — ON CONFLICT DO NOTHING 전제)
CREATE UNIQUE INDEX IF NOT EXISTS uq_violation_event_id
    ON violation_log (event_id)
    WHERE event_id IS NOT NULL;

-- intersection_id NOT NULL 해제 (FastAPI webhook은 교차로 ID 미제공)
ALTER TABLE violation_log ALTER COLUMN intersection_id DROP NOT NULL;