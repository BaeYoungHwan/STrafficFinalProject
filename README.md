<div align="center">
  <img src="AIpassFrontend/src/assets/logos/AI-PASS_LOGO.png" alt="AIpass Logo" width="180"/>
  <h1>AIpass</h1>
  <p><strong>스마트 교차로 무인 단속 및 예지보전 모니터링 시스템</strong></p>

  ![Vue 3](https://img.shields.io/badge/Vue-3.x-42b883?logo=vue.js&logoColor=white)
  ![Spring Boot](https://img.shields.io/badge/Spring_Boot-3.x-6DB33F?logo=springboot&logoColor=white)
  ![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?logo=fastapi&logoColor=white)
  ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
  ![YOLO](https://img.shields.io/badge/YOLO-ultralytics-FF6600?logo=yolo&logoColor=white)
</div>

---

실시간 CCTV 영상 분석으로 **과속·실선침범 차량을 자동 단속**하고, 교통 인프라 장비의 **예지보전**을 지원하는 스마트 교차로 통합 관리 플랫폼입니다.

---

## 팀 구성

| 이름 | 역할 |
|------|------|
| 배영환 | PM / AI 서버 전체 (FastAPI, YOLO, OCR, 예지보전 ML) / 과속·실선침범 단속 / 대시보드 / CCTV / 단속 내역 / 교통 신호 제어 화면 |
| 김소연 | DB 설계 (ERD, 14개 테이블) / 화면 기획·UX / 통계 화면 |
| 하재영 | 로그인·회원가입·마이페이지 화면 / 예지보전 화면 |

---

## 기술 스택

| 서버 | 스택 | 포트 |
|------|------|------|
| Frontend | Vue 3 + Vite, Pinia, Vue Router 4, Axios, Chart.js | 5173 |
| Backend | Spring Boot, MyBatis, PostgreSQL 17, HttpSession, BCrypt | 9000 |
| AI 서버 | FastAPI, YOLO (ultralytics), ByteTrack, PaddleOCR, EasyOCR, OpenCV, XGBoost | 8000 |
| DB | PostgreSQL 17 | 5432 |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                  Vue Frontend (:5173)                        │
│  Dashboard │ CCTV │ Enforcement │ Traffic │ Predictive       │
└──────────────────────┬──────────────────────────────────────┘
                       │ Axios (Vite proxy /api → :9000)
                       │ SSE /api/notifications/stream
┌──────────────────────▼──────────────────────────────────────┐
│               Spring Boot Backend (:9000)                    │
│  Auth │ Member │ CCTV │ Dashboard │ Enforcement              │
│  Traffic │ Sensor │ Predictive │ Notifications(SSE)          │
│                   MyBatis + PostgreSQL 17                    │
└───────┬─────────────────────────────────┬────────────────────┘
        │ Webhook POST (위반 이벤트)        │ POST /api/sensor/ingest
┌───────▼──────────────┐    ┌─────────────▼──────────────────┐
│  FastAPI SPEED (:8000)│    │ FastAPI PREDICTIVE (:8000)     │
│  FEATURE_MODE=SPEED   │    │  XGBoost 이상탐지 + 고장분류    │
│  과속 감지 파이프라인  │    │  12대 장비 센서 시뮬레이션      │
└──────────────────────┘    └────────────────────────────────┘
┌──────────────────────┐
│  FastAPI LINE (:8000) │
│  FEATURE_MODE=LINE    │
│  실선침범 감지 파이프라인│
└──────────────────────┘
```

### 시연 배포 구성 (4대 PC)

| PC | IP | 역할 |
|----|-----|------|
| 시연 컴퓨터 | `192.168.100.173` | Frontend (:5173) + Backend (:9000) |
| 과속 PC | `192.168.100.112` | FastAPI `FEATURE_MODE=SPEED` |
| 침범 PC | `192.168.100.59` | FastAPI `FEATURE_MODE=LINE_CROSSING` |
| 예지보전 PC | `192.168.100.29` | FastAPI 예지보전 + PostgreSQL (:5432) |

- DB(`aipass`)는 `.29`에서 운영, 모든 PC가 동일 DB에 연결
- FastAPI 위반 이벤트는 `.173:9000` Backend로 webhook 전송

---

## 화면 구성 및 스크린샷

| 화면 | 경로 | 미리보기 |
|------|------|---------|
| 로그인 | `/login` | — |
| 회원가입 | `/signup` | — |
| ID/비번 찾기 | `/find-account` | — |
| 대시보드 | `/` | ![대시보드](assets/screenshots/screenshot_dashboard.png) |
| 마이페이지 | `/mypage` | — |
| 교통 신호 제어 | `/traffic` | ![교통신호제어](assets/screenshots/screenshot_traffic.png) |
| CCTV 모니터링 | `/cctv` | ![CCTV](assets/screenshots/screenshot_cctv.png) |
| 단속 내역 | `/enforcement` | ![단속내역](assets/screenshots/screenshot_enforcement.png) |
| 예지보전 | `/predictive` | ![예지보전](assets/screenshots/screenshot_predictive.png) |
| 예지보전 상세 | `/predictive/:id` | ![예지보전상세](assets/screenshots/screenshot_predictive_detail.png) |
| 통계 | `/statistics` | ![통계](assets/screenshots/screenshot_statistics.png) |

---

## 주요 기능

### 과속 단속 자동화 (`FEATURE_MODE=SPEED`)
- YOLO + ByteTrack으로 차량 객체 추적
- 호모그래피 행렬 + EMA 필터로 실시간 속도 계산
- 70 km/h 초과 연속 5프레임 → 위반 확정 + 이벤트 발생
- 동일 차량 10초 쿨다운으로 중복 단속 방지

### 실선침범 단속 자동화 (`FEATURE_MODE=LINE_CROSSING`)
- 양방향 (하행선·상행선) 2중 실선 감지
- 차량 중심점이 선을 가로지를 때 침범 이벤트 발생
- 동일 차량 3초 쿨다운

### 번호판 OCR (5단계 폴백)
1. 원본 이미지 직접 OCR (PaddleOCR)
2. 야간 대비 CLAHE 보정 후 OCR (PaddleOCR)
3. HSV 컨투어 기반 번호판 영역 탐지 후 OCR (PaddleOCR)
4. 슬라이딩 윈도우 OCR (PaddleOCR Legacy)
5. EasyOCR 폴백

### 혼잡도 분석
| 레벨 | 조건 | 표시 |
|------|------|------|
| SMOOTH | 차량 0~5대 | 원활 |
| SLOW | 차량 6~15대 | 서행 |
| CONGESTED | 차량 16대 이상 | 혼잡 |

### Webhook + DLQ 패턴
- 위반 이벤트 → Spring Boot webhook → 실패 시 `fallback_queue.jsonl` 적재
- 5분 주기 자동 재시도 / 수동 즉시 재전송 API

### 예지보전 AI (`/api/v1/predict`)
- XGBoost 이상탐지 (binary) + 고장분류 3-class (BEARING / COMPOUND / MOTOR)
- 온도·진동·전류·위험도 등 12개 센서 데이터 배치 판정
- 위험 등급 자동 산출 → `sensor_log` 저장 → 장비 상태 머신 갱신

### SSE 실시간 알림 (`/api/notifications/stream`)
- 위반 이벤트 발생 시 Frontend로 즉시 푸시
- 하트비트 포함, 타임아웃 없음

### CCTV URL 자동 갱신
- ITS Open API → `cctv_info` 테이블 4시간 주기 자동 갱신
- FastAPI 기동 시 즉시 1회 실행

### 날씨 데이터 자동 수집
- Naver Weather 스크래핑 → `weather_log` 자동 저장
- 매일 오전 9시 정기 수집

---

## 실행 방법

### 사전 요구사항
- PostgreSQL 17 (`localhost:5432`, DB: `aipass`, user: `postgres`, pw: `1234`)
- Python 3.10+
- Node.js 18+
- Java 17+

### 서버 시작 순서 (순서 준수 필수)

```bash
# 1. PostgreSQL 17 먼저 시작

# 2. Backend (포트 9000)
# IntelliJ/Eclipse에서 AIpassBackend 프로젝트 Run

# 3. AI 서버 (포트 8000)
cd AIpassFastAPI
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 4. Frontend (포트 5173)
cd AIpassFrontend
npm install
npm run dev
```

### AI 서버 환경 변수 (`.env`)

```env
# 기능 모드 선택: SPEED (과속) | LINE_CROSSING (실선침범)
FEATURE_MODE=SPEED

BACKEND_URL=http://localhost:9000
FASTAPI_URL=http://localhost:8000
VIDEO_SOURCE_URL=<RTSP 또는 영상 파일 경로>

# YOLO 설정
YOLO_MODEL=yolo26n.pt
CONF_THRESHOLD=0.4
SPEED_SCALE_FACTOR=1.0

# DB 직접 연결 (CCTV URL 갱신용)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aipass
DB_USER=postgres
DB_PASSWORD=1234

# ITS Open API (CCTV URL 자동갱신)
CCTV_INFO_URL=<ITS_API_URL>
```

### 기능 모드별 `.env` 파일

```bash
# 과속 단속 PC
cp .env.speed .env && uvicorn main:app --host 0.0.0.0 --port 8000

# 실선침범 단속 PC
cp .env.line .env && uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 프로젝트 구조

```
STrafficFinalProject/
├── AIpassFrontend/src/
│   ├── api/index.js              ← Axios 인스턴스 (withCredentials: true)
│   ├── components/               ← MainLayout, Header, Sidebar, Footer
│   ├── router/index.js           ← 인증 라우터 가드
│   ├── stores/
│   │   ├── auth.js               ← Pinia (세션 기반 인증)
│   │   └── notification.js       ← SSE 알림 스토어
│   └── views/                    ← *View.vue 파일들
│
├── AIpassBackend/src/main/java/com/aipass/
│   ├── controller/
│   │   ├── AuthController.java
│   │   ├── MemberController.java
│   │   ├── TrafficController.java
│   │   ├── CctvController.java
│   │   ├── DashboardController.java
│   │   ├── EnforcementController.java
│   │   ├── SensorController.java       ← 센서 배치 수집 + ML 클라이언트
│   │   ├── NotificationController.java ← SSE 알림
│   │   └── PredictiveController.java   ← 예지보전 장비/센서 API
│   ├── dao/                      ← MyBatis Mapper 인터페이스
│   ├── dto/                      ← 데이터 전송 객체
│   ├── service/                  ← MemberService (BCrypt), EquipmentStateMachineService
│   ├── LoginInterceptor.java     ← 세션 기반 인증
│   └── resources/sqls/           ← MyBatis XML
│
├── AIpassFastAPI/
│   ├── main.py                   ← 앱 진입점 (lifespan, AI-Target 동적 적용)
│   ├── core/
│   │   ├── config.py             ← pydantic-settings v2 (FEATURE_MODE 포함)
│   │   └── hardware.py           ← GPU/CPU 가속 감지
│   ├── api/
│   │   ├── stream.py             ← MJPEG + 위반 목록 + DLQ 재전송
│   │   ├── cctv.py               ← CCTV 목록/단건 조회
│   │   └── predictive.py         ← 예지보전 센서 판정 엔드포인트
│   ├── services/
│   │   ├── vision.py             ← VisionEngine (3-Process 파이프라인)
│   │   ├── speed_detector.py     ← 호모그래피 + EMA
│   │   ├── line_detector.py      ← 실선침범 감지 (양방향)
│   │   ├── aggregator.py         ← 혼잡도 엔진 + DLQ 스케줄러
│   │   ├── ocr_storage.py        ← PaddleOCR 4단계 + EasyOCR 폴백
│   │   ├── webhook_client.py     ← Webhook + DLQ 패턴
│   │   ├── violation_cache.py    ← 인메모리 순환 캐시
│   │   ├── cctv_refresher.py     ← ITS API → DB CCTV URL 자동갱신
│   │   ├── weather_scraper.py    ← Naver Weather → weather_log 수집
│   │   └── predictive/
│   │       ├── judge.py          ← XGB 이상탐지 + 3-class 고장분류
│   │       ├── simulator.py      ← 12대 센서 시뮬레이션
│   │       ├── scheduler.py      ← 장비 상태 스케줄러
│   │       └── state.py          ← 장비 상태 관리
│   ├── data/
│   │   ├── numberplate/          ← 번호판 크롭 이미지
│   │   ├── carnumber/            ← OCR 테스트 샘플
│   │   └── fallback_queue.jsonl  ← DLQ 파일
│   └── requirements.txt
│
└── docs/claude-ref/              ← 개발 참고 문서
```

---

## API 엔드포인트

### FastAPI (`http://localhost:8000`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/stream/video` | MJPEG 실시간 스트리밍 |
| POST | `/api/v1/stream/source` | 영상 소스 URL 변경 |
| GET | `/api/v1/stream/status` | VisionEngine 상태 확인 |
| GET | `/api/v1/stream/violations` | 최근 위반 목록 (캐시) |
| POST | `/api/v1/stream/retry-dlq` | DLQ 즉시 재전송 |
| GET | `/api/v1/cctv/list` | 활성 CCTV 목록 |
| GET | `/api/v1/cctv/{id}` | CCTV 단건 조회 |
| POST | `/api/v1/predict` | 센서 데이터 배치 판정 (이상탐지 + 고장분류) |
| GET | `/health` | 헬스체크 |

### Spring Boot (`http://localhost:9000`)

| 모듈 | 경로 | 주요 기능 |
|------|------|----------|
| 인증 | `/api/auth/*` | 로그인, 회원가입, ID/비번 찾기, 재설정 |
| 회원 | `/api/member/*` | 프로필 조회/수정, 비밀번호 변경 |
| CCTV | `/api/cctv/*` | CCTV 목록, 단건 조회, AI 대상 조회 |
| 단속 | `/api/enforcement/*` | Webhook 수신, 위반 목록/상세/상태변경/수정 |
| 대시보드 | `/api/dashboard/*` | 날씨, 위반 요약, 혼잡도, 교통량, CCTV 상태 |
| 교통 | `/api/traffic/*` | 교차로 목록, 신호 타이밍 제어 |
| 센서 | `/api/sensor/ingest` | 센서 배치 수집 + ML 클라이언트 호출 |
| 알림 | `/api/notifications/*` | SSE 스트림 (하트비트), 최근 50건 조회 |
| 예지보전 | `/api/predictive/*` | 장비 목록/상세/센서 로그/상태 리셋 |
| 통계 | `/api/statistics/*` | 교통·단속·예지보전·날씨 통계 집계 |

---

## 데이터베이스 주요 테이블

| 테이블 | 설명 |
|--------|------|
| `member` | 사용자 계정 (BCrypt 암호화) |
| `intersection` | 교차로 위치 정보 (위경도, 신호 타이밍) |
| `violation_log` | 위반 기록 (UNPROCESSED / APPROVED / REJECTED) |
| `cctv_info` | CCTV 장치 정보 및 스트림 URL |
| `equipment` | 교통 인프라 장비 |
| `sensor_log` | 장비 센서 로그 (온도, 진동, 전류, 위험도) |
| `traffic_flow_log` | ITS 구간별 교통 흐름 및 혼잡도 |
| `weather_log` | 교차로별 기상 데이터 |
| `its_route` | ITS 수집 노선 정보 |
| `its_collect_log` | ITS 수집 이력 |
| `maintenance_log` | 유지보수 티켓 |
| `signal_control_log` | 신호 제어 이력 |
| `traffic_congestion` | 혼잡도 기록 |

---

## 개발 주의사항

| 금지 | 이유 |
|------|------|
| Spring Security 추가 | `LoginInterceptor.java`가 인증 담당 — 충돌 발생 |
| JWT 도입 | `HttpSession` 기반 인증 구조 유지 |
| MyBatis 어노테이션 방식 | `sqls/*.xml` XML 방식만 사용 |
| Axios baseURL 절대 URL 변경 | Vite 프록시 + `withCredentials` 구조 파괴 |
