# AIpass — 스마트 교차로 무인 단속 및 예지보전 모니터링 시스템

실시간 CCTV 영상 분석을 통해 과속 차량을 자동 단속하고, 교통 인프라 장비의 예지보전을 지원하는 스마트 교차로 통합 관리 플랫폼입니다.

---

## 팀 구성

| 이름 | 역할 |
|------|------|
| 배영환 | PM / AI 서버 (FastAPI, YOLO, 번호판 OCR) / 단속 내역 / 교통 신호 제어 화면 |
| 김소연 | 기획 / DB (ERD, 화면 설계, 테스트) |
| 하재영 | 대시보드 화면 / 예지보전 AI / CCTV 화면 |

---

## 기술 스택

| 서버 | 스택 | 포트 |
|------|------|------|
| Frontend | Vue 3 + Vite, Pinia, Vue Router 4, Axios, Chart.js | 5173 |
| Backend | Spring Boot, MyBatis, PostgreSQL 17, HttpSession | 9000 |
| AI 서버 | FastAPI, YOLO (ultralytics), PaddleOCR, OpenCV | 8000 |
| DB | PostgreSQL 17 | 5432 |

---

## 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│               Vue Frontend (:5173)                       │
│  Dashboard │ CCTV │ Enforcement │ Traffic │ Predictive  │
└──────────────────────┬──────────────────────────────────┘
                       │ Axios (Vite proxy /api → :9000)
┌──────────────────────▼──────────────────────────────────┐
│              Spring Boot Backend (:9000)                 │
│  Auth │ Member │ CCTV │ Dashboard │ Enforcement │ Traffic│
│                  MyBatis + PostgreSQL 17                 │
└───────────────┬──────────────────────────────────────────┘
                │ Webhook POST (위반 이벤트)
┌───────────────▼──────────────────────────────────────────┐
│              FastAPI AI Server (:8000)                   │
│                                                          │
│  [Process A] video_reader_worker                         │
│      RTSP/HTTP → SharedMemory → meta_queue               │
│                                                          │
│  [Process B] ai_inference_worker                         │
│      YOLO + ByteTrack + 호모그래피/EMA 속도 계산           │
│      → mjpeg_queue + event_queue                         │
│                                                          │
│  [Process C] process_event_loop                          │
│      PaddleOCR 4단계 폴백 → Webhook 전송 + DLQ           │
└──────────────────────────────────────────────────────────┘
```

---

## 주요 기능

### 과속 단속 자동화
- YOLO + ByteTrack으로 차량 추적
- 호모그래피 행렬 + EMA 필터로 실시간 속도 계산
- 70 km/h 초과 연속 5프레임 시 위반 확정 및 이벤트 발생

### 번호판 OCR (PaddleOCR 4단계 폴백)
1. 원본 이미지 직접 OCR
2. 야간 대비 CLAHE 보정 후 OCR
3. HSV 컨투어 기반 번호판 영역 탐지 후 OCR
4. 슬라이딩 윈도우 OCR

### 혼잡도 분석
| 레벨 | 조건 | 표시 |
|------|------|------|
| SMOOTH | 차량 0~5대 | 원활 |
| SLOW | 차량 6~15대 | 서행 |
| CONGESTED | 차량 16대 이상 | 혼잡 |

### Webhook + DLQ 패턴
- 위반 이벤트 → Spring Boot webhook 전송 → 실패 시 `fallback_queue.jsonl` 적재
- 5분 주기 자동 재시도 / 수동 즉시 재전송 API 제공

### 대시보드
- 카카오맵 기반 교차로 위치 시각화
- 날씨 정보 / 오늘 위반 요약 / 구간별 혼잡도 / CCTV 상태 실시간 표시

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
BACKEND_URL=http://localhost:9000
FASTAPI_URL=http://localhost:8000
VIDEO_SOURCE_URL=<RTSP 또는 영상 파일 경로>
YOLO_MODEL=yolo26n.pt
CONF_THRESHOLD=0.3
SPEED_SCALE_FACTOR=1.0
```

---

## 프로젝트 구조

```
STrafficFinalProject/
├── AIpassFrontend/src/
│   ├── api/index.js          ← Axios 인스턴스 (withCredentials: true)
│   ├── components/           ← MainLayout, Header, Sidebar, Footer
│   ├── router/index.js       ← 인증 라우터 가드
│   ├── stores/auth.js        ← Pinia (세션 기반 인증)
│   └── views/                ← *View.vue 파일들
│
├── AIpassBackend/src/main/java/com/aipass/
│   ├── controller/           ← Auth, Member, Traffic, CCTV, Dashboard, Enforcement
│   ├── dao/                  ← MyBatis Mapper 인터페이스
│   ├── dto/                  ← 데이터 전송 객체
│   ├── service/              ← MemberService (BCrypt)
│   ├── LoginInterceptor.java ← 세션 기반 인증
│   └── resources/sqls/       ← MyBatis XML
│
├── AIpassFastAPI/
│   ├── main.py               ← 앱 진입점 (lifespan 관리)
│   ├── core/config.py        ← pydantic-settings v2 설정
│   ├── api/stream.py         ← REST API (/api/v1/stream/*)
│   ├── services/
│   │   ├── vision.py         ← VisionEngine (3-Process 파이프라인)
│   │   ├── speed_detector.py ← 호모그래피 + EMA
│   │   ├── aggregator.py     ← 혼잡도 엔진 + DLQ 스케줄러
│   │   ├── ocr_storage.py    ← PaddleOCR 4단계 폴백
│   │   ├── webhook_client.py ← Webhook + DLQ 패턴
│   │   └── violation_cache.py ← 인메모리 순환 캐시
│   ├── data/
│   │   ├── numberplate/      ← 번호판 크롭 이미지 저장
│   │   ├── carnumber/        ← OCR 테스트용 차량 샘플
│   │   └── fallback_queue.jsonl ← DLQ 파일
│   └── requirements.txt
│
└── docs/claude-ref/          ← 개발 참고 문서
```

---

## API 엔드포인트 요약

### FastAPI (`http://localhost:8000`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/stream/video` | MJPEG 실시간 스트리밍 |
| POST | `/api/v1/stream/source` | 영상 소스 URL 변경 |
| GET | `/api/v1/stream/status` | VisionEngine 상태 확인 |
| GET | `/api/v1/stream/violations` | 최근 위반 목록 (캐시) |
| POST | `/api/v1/stream/retry-dlq` | DLQ 즉시 재전송 |
| GET | `/health` | 헬스체크 |

### Spring Boot (`http://localhost:9000`)

| 모듈 | 경로 | 주요 기능 |
|------|------|----------|
| 인증 | `/api/auth/*` | 로그인, 회원가입, ID/비번 찾기 |
| 회원 | `/api/member/*` | 프로필 조회/수정, 비밀번호 변경 |
| CCTV | `/api/cctv/*` | CCTV 목록, 단건 조회, AI 대상 |
| 단속 | `/api/enforcement/*` | 위반 목록/상세/상태변경, webhook 수신 |
| 대시보드 | `/api/dashboard/*` | 날씨, 위반 요약, 혼잡도, 교통량 |
| 교통 | `/api/traffic/*` | 교차로 목록, 신호 타이밍 제어 |

---

## 화면 구성

| 화면 | 경로 | 상태 |
|------|------|------|
| 로그인 | `/login` | 완료 |
| 회원가입 | `/signup` | 완료 |
| ID/비번 찾기 | `/find-account` | 완료 |
| 대시보드 | `/` | 완료 |
| 마이페이지 | `/mypage` | 완료 |
| 교통 신호 제어 | `/traffic` | 완료 |
| CCTV 모니터링 | `/cctv` | 완료 |
| 단속 내역 | `/enforcement` | 완료 |
| 예지보전 | `/predictive` | 개발 예정 |
| 통계 | `/statistics` | 개발 예정 |

---

## 데이터베이스 주요 테이블

| 테이블 | 설명 |
|--------|------|
| `member` | 사용자 계정 (BCrypt 암호화) |
| `violation_log` | 과속 위반 기록 (UNPROCESSED / APPROVED / REJECTED) |
| `cctv_info` | CCTV 장치 정보 및 스트림 URL |
| `intersection` | 교차로 위치 정보 (위경도) |
| `equipment` | 교통 인프라 장비 |
| `sensor_log` | 장비 센서 로그 (온도, 진동, 위험도) |
| `traffic_flow_log` | 구간별 교통 흐름 및 혼잡도 |
| `weather_log` | 교차로별 기상 데이터 |

---

## 개발 주의사항

| 금지 | 이유 |
|------|------|
| Spring Security 추가 | `LoginInterceptor.java`가 인증 담당 — 충돌 발생 |
| JWT 도입 | `HttpSession` 기반 인증 구조 유지 |
| MyBatis 어노테이션 방식 | `sqls/*.xml` XML 방식만 사용 |
| Axios baseURL 절대 URL 변경 | Vite 프록시 + `withCredentials` 구조 파괴 |
