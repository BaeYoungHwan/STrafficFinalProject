# AIpass 프로젝트 전체 코드베이스 분석 보고서

> 작성일: 2026-03-20
> 분석 범위: Spring Boot Backend + Vue 3 Frontend 전체 소스코드

---

## 1. 프로젝트 개요

**AIpass**는 스마트 교차로 무인 단속 및 예지보전 모니터링 시스템으로, Spring Boot 백엔드 + Vue 3 프론트엔드 + FastAPI AI 서버로 구성된다.

| 구분 | 기술 | 포트 |
|------|------|------|
| Frontend | Vue 3 + Vite + Pinia + Axios + Chart.js | 5173 |
| Backend | Spring Boot 4.0.3 + MyBatis + PostgreSQL | 9000 |
| Database | PostgreSQL 17 | 5432 |
| AI Server | FastAPI (별도) | 미정 |

---

## 2. 백엔드 아키텍처

### 2.1 패키지 구조

```
com.aipass/
├── AipassApplication.java          ← Spring Boot 메인
├── DatabaseConfig.java              ← HikariCP + MyBatis 설정
├── WebConfigurer.java               ← CORS + 인터셉터 등록
├── LoginInterceptor.java            ← 세션 기반 인증 검증
├── controller/
│   ├── AuthController.java          ← 로그인/회원가입/계정찾기
│   ├── MemberController.java        ← 프로필/비밀번호 변경
│   ├── TrafficController.java       ← 교통 신호 (더미 데이터)
│   └── EnforcementController.java   ← 단속 내역 (실제 DB 연동)
├── service/
│   └── MemberService.java           ← 회원 비즈니스 로직
├── dao/
│   ├── MemberMapper.java            ← 회원 SQL 매퍼
│   └── ViolationMapper.java         ← 단속 SQL 매퍼
├── dto/
│   ├── MemberDTO.java
│   ├── LoginRequest.java
│   ├── LoginResponse.java
│   ├── SignupRequest.java
│   ├── ViolationDTO.java
│   ├── IntersectionDTO.java
│   └── TrafficFlowDTO.java
└── resources/
    ├── application.properties
    └── sqls/
        ├── member.xml               ← 회원 관련 쿼리 8개
        └── violation.xml            ← 단속 관련 쿼리 5개
```

### 2.2 설정

| 항목 | 값 |
|------|-----|
| 서버 포트 | 9000 |
| DB | PostgreSQL `aipass` (localhost:5432, postgres/1234) |
| 세션 타임아웃 | 1800초 (30분) |
| 세션 쿠키 | HTTP-only, SameSite=Lax |
| CORS | 모든 origin 허용, credentials: true |
| ORM | MyBatis (camelCase↔snake_case 자동매핑) |
| 비밀번호 암호화 | BCrypt (Spring Security Crypto) |
| API 키 | ITS API, 기상청 API (환경변수로 관리) |

### 2.3 인증 체계

- **방식:** HttpSession 기반 (JWT 미사용)
- **세션 속성:** `loginMember` → MemberDTO 객체 저장
- **인터셉터:** `/api/**` 전체에 적용, 아래 경로 제외:
  - `/api/auth/login`, `/api/auth/signup`, `/api/auth/check-username`
  - `/api/auth/find-id`, `/api/auth/verify-reset`, `/api/auth/reset-password`
  - `/api/enforcement/webhook` (FastAPI 콜백)
- **미인증 시:** 401 응답 + `"로그인이 필요합니다."` 메시지

---

## 3. API 엔드포인트 전체 목록

### 3.1 AuthController (`/api/auth`) — 공개 + 인증

| Method | 경로 | 인증 | 기능 | 상태 |
|--------|------|------|------|------|
| POST | `/auth/login` | 공개 | 로그인 (username, password) → 세션 생성 | ✅ DB 연동 |
| POST | `/auth/logout` | 인증 | 세션 무효화 | ✅ 동작 |
| GET | `/auth/check` | 인증 | 로그인 상태 확인 | ✅ 동작 |
| GET | `/auth/check-username` | 공개 | 아이디 중복 확인 | ✅ DB 연동 |
| POST | `/auth/find-id` | 공개 | 이름+이메일로 아이디 찾기 (마스킹 처리) | ✅ DB 연동 |
| POST | `/auth/verify-reset` | 공개 | 비밀번호 재설정 본인 확인 | ✅ DB 연동 |
| POST | `/auth/reset-password` | 공개 | 비밀번호 재설정 | ✅ DB 연동 |
| POST | `/auth/signup` | 공개 | 회원가입 | ✅ DB 연동 |

### 3.2 MemberController (`/api/member`) — 인증 필요

| Method | 경로 | 기능 | 상태 |
|--------|------|------|------|
| GET | `/member/profile` | 내 프로필 조회 | ✅ DB 연동 |
| PUT | `/member/profile` | 프로필 수정 (이름, 이메일) | ✅ DB 연동 |
| POST | `/member/change-password` | 비밀번호 변경 | ✅ DB 연동 |

### 3.3 TrafficController (`/api/traffic`) — 인증 필요

| Method | 경로 | 기능 | 상태 |
|--------|------|------|------|
| GET | `/traffic/intersections` | 교차로 목록 (8개) | ⚠️ 더미 데이터 |
| GET | `/traffic/intersections/{id}` | 교차로 상세 | ⚠️ 더미 데이터 |
| GET | `/traffic/flow/{intersectionId}` | 시간대별 교통량 (15건) | ⚠️ 더미 데이터 |
| GET | `/traffic/summary` | 교차로 요약 통계 | ⚠️ 더미 데이터 |
| POST | `/traffic/intersections/{id}/signal` | 신호 변경 적용 | ⚠️ 더미 응답 |

### 3.4 EnforcementController (`/api/enforcement`) — 혼합

| Method | 경로 | 인증 | 기능 | 상태 |
|--------|------|------|------|------|
| POST | `/enforcement/webhook` | 공개 | FastAPI 위반 이벤트 수신 | ✅ DB 연동 |
| GET | `/enforcement/violations` | 인증 | 단속 내역 목록 (페이징+필터) | ✅ DB 연동 |
| GET | `/enforcement/violations/{id}` | 인증 | 단속 상세 조회 | ✅ DB 연동 |
| PUT | `/enforcement/violations/{id}/status` | 인증 | 상태 변경 (승인/반려) | ✅ DB 연동 |

**통계:** 공개 엔드포인트 7개, 인증 필요 12개, DB 연동 14개, 더미 데이터 5개

---

## 4. 데이터베이스 스키마 (코드 기반 추론)

### 4.1 member 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| member_id | BIGSERIAL PK | 자동증가 PK |
| login_id | VARCHAR UNIQUE | 로그인 아이디 |
| password | VARCHAR | BCrypt 해시 |
| name | VARCHAR | 사용자 이름 |
| email | VARCHAR | 이메일 |
| created_at | TIMESTAMP | 생성일시 (NOW()) |

### 4.2 violation_log 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| violation_id | BIGSERIAL PK | 자동증가 PK |
| event_id | VARCHAR UNIQUE | FastAPI 이벤트 ID (중복방지) |
| intersection_id | BIGINT (nullable) | 교차로 FK |
| plate_number | VARCHAR | 차량 번호판 |
| violation_type | VARCHAR | 위반유형 (과속/신호위반/중앙선침범/차선위반) |
| image_url | VARCHAR (nullable) | CCTV 캡처 이미지 URL |
| fine_status | VARCHAR | 상태 (UNPROCESSED/APPROVED/REJECTED) |
| is_corrected | BOOLEAN | 보정 여부 |
| speed_kmh | NUMERIC | 단속 속도 |
| detected_at | TIMESTAMP WITH TZ | 위반 감지 일시 |

### 4.3 주요 SQL 쿼리

**member.xml (8개):**
- `findByLoginId` — 로그인 ID로 회원 조회
- `countByLoginId` — 중복 체크
- `insertMember` — 회원가입 (created_at = NOW())
- `findByNameAndEmail` — 아이디 찾기
- `findByLoginIdAndEmail` — 비밀번호 재설정 인증
- `updatePassword` — 비밀번호 변경
- `updateMember` — 프로필 수정

**violation.xml (5개):**
- `findAll` — 조건 검색 + 페이징 (ILIKE 검색, LIMIT/OFFSET)
- `countAll` — 총 건수 (동일 WHERE 조건)
- `findById` — 단건 조회
- `insert` — 위반 등록 (ON CONFLICT event_id DO NOTHING)
- `updateStatus` — 상태 변경

---

## 5. 프론트엔드 아키텍처

### 5.1 기술 스택

| 항목 | 버전 |
|------|------|
| Vue | 3.5.25 |
| Vite | 8.0.0-beta.13 |
| Vue Router | 5.0.3 |
| Pinia | 3.0.4 |
| Axios | 1.13.6 |
| Chart.js | 4.5.1 |

### 5.2 파일 구조

```
aipassfrontend/src/
├── main.js                    ← 앱 초기화 (Pinia + Router)
├── App.vue                    ← 루트 컴포넌트
├── api/
│   └── index.js               ← Axios 인스턴스 (baseURL: /api, 401 핸들링)
├── stores/
│   └── auth.js                ← Pinia 인증 스토어 (user, isLoggedIn)
├── router/
│   └── index.js               ← 라우트 정의 + beforeEach 가드
├── components/
│   ├── MainLayout.vue         ← Header + Sidebar + Content + Footer 조합
│   ├── Header.vue             ← 로고 + 로그아웃/마이페이지 버튼
│   ├── Sidebar.vue            ← GNB 네비게이션 (6개 메뉴)
│   └── Footer.vue             ← 팀원 이름 + 기업 로고
└── views/
    ├── LoginView.vue          ← ✅ 완성
    ├── SignupView.vue         ← ✅ 완성
    ├── FindAccountView.vue    ← ✅ 완성
    ├── MypageView.vue         ← ✅ 완성
    ├── TrafficView.vue        ← ✅ 완성
    ├── EnforcementView.vue    ← ✅ 완성
    ├── DashboardView.vue      ← ⏳ 플레이스홀더
    ├── CctvView.vue           ← ⏳ 플레이스홀더
    ├── PredictiveView.vue     ← ⏳ 플레이스홀더
    └── StatisticsView.vue     ← ⏳ 플레이스홀더
```

### 5.3 라우팅

**공개 라우트 (인증 불필요):**

| 경로 | 컴포넌트 | 기능 |
|------|----------|------|
| `/login` | LoginView | 로그인 |
| `/signup` | SignupView | 회원가입 |
| `/find-account` | FindAccountView | 아이디/비밀번호 찾기 |

**보호 라우트 (인증 필요, MainLayout 감싸기):**

| 경로 | 컴포넌트 | 기능 |
|------|----------|------|
| `/` | DashboardView | 메인 대시보드 |
| `/mypage` | MypageView | 프로필/비밀번호 관리 |
| `/traffic` | TrafficView | 교통/신호 제어 |
| `/cctv` | CctvView | CCTV 모니터링 |
| `/enforcement` | EnforcementView | 단속 내역 |
| `/predictive` | PredictiveView | 설비 예지보전 |
| `/statistics` | StatisticsView | 통계 |

**라우트 가드:** `router.beforeEach` → Pinia auth 스토어로 세션 확인 → 미인증 시 `/login` 리다이렉트

### 5.4 상태 관리 (Pinia)

```javascript
// stores/auth.js
state: {
  user: null,        // { username, name }
  isLoggedIn: false
}
actions: {
  login(username, password)   // POST /auth/login → 세션 생성
  logout()                    // POST /auth/logout → 세션 파기
  checkSession()              // GET /auth/check → 세션 유효성 검증
}
```

### 5.5 HTTP 클라이언트

```javascript
// api/index.js
baseURL: '/api'              // Vite 프록시 → http://localhost:9000
timeout: 10000               // 10초
withCredentials: true         // 세션 쿠키 포함
// 401 인터셉터: 자동으로 /login 리다이렉트
```

---

## 6. 화면별 상세 분석

### 6.1 LoginView (로그인) ✅

- 중앙 정렬 카드 형태, iOS 디자인
- 아이디/비밀번호 입력 → `auth.login()` 호출 → `/` 리다이렉트
- 에러 메시지 인라인 표시
- "아이디 찾기" 링크 → `/find-account`
- 회원가입 버튼 → `/signup`

### 6.2 SignupView (회원가입) ✅

- **아이디:** 4자 이상 + 중복확인 버튼 (`GET /auth/check-username`)
- **비밀번호:** 8~16자, 대문자+소문자+숫자+특수문자 필수, 실시간 규칙 표시 (빨강→초록)
- **비밀번호 확인:** 일치 여부 검증
- **이름:** 2자 이상, 한글 또는 영문
- **이메일:** 이메일 형식 검증
- 가입 완료 시 자동 로그인 → `/` 리다이렉트
- 유효성 오류 시 shake 애니메이션

### 6.3 FindAccountView (아이디/비밀번호 찾기) ✅

- **4단계 플로우:**
  1. 유형 선택 (아이디 찾기 / 비밀번호 재설정)
  2. 이름+이메일 입력 → `POST /auth/find-id` (마스킹된 아이디 표시)
  3. 아이디+이메일 입력 → `POST /auth/verify-reset` (본인 확인)
  4. 새 비밀번호 입력 → `POST /auth/reset-password` → `/login` 리다이렉트

### 6.4 MypageView (마이페이지) ✅

- **2컬럼 레이아웃:**
  - **좌:** 프로필 카드 (읽기 전용 → 수정 모드 전환, `PUT /member/profile`)
  - **우:** 비밀번호 변경 카드 (현재 비밀번호 확인 + 새 비밀번호 규칙 검증, `POST /member/change-password`)
- 성공 메시지 3초 후 자동 소멸
- 각 카드 독립적 로딩/에러/성공 상태

### 6.5 TrafficView (교통/신호 제어) ✅

- **상단 4개 요약 카드:** 총 교차로 / 정상 운영 / 이상 신호 / 혼잡 구간
- **좌:** 교차로 목록 (스크롤, 상태 도트 + 이름 + 위치 + 혼잡도 뱃지)
- **우 (선택 시):**
  - 신호등 시각화 (빨강/노랑/초록 on/off 상태)
  - 현재 단계 + 잔여 시간 표시
  - 신호 시간 입력 (초록 10~120초, 노랑 3~10초, 빨강 10~120초)
  - 총 주기 시간 자동 계산
  - Chart.js 복합 차트 (막대: 교통량 + 라인: 평균속도)
  - 시간대별 교통 흐름 테이블

### 6.6 EnforcementView (단속 내역) ✅

- **상단 필터:** 차량번호(검색) + 위반유형(드롭다운) + 상태(드롭다운) + 조회/초기화
- **좌:** 단속 목록 테이블 (10건/페이지, 페이지네이션)
  - 컬럼: 번호 | 차량번호 | 위반유형 | 위치 | 상태
  - 상태 뱃지: 대기중(노랑) / 승인(초록) / 반려(빨강)
- **우 (선택 시):** 상세 정보 패널
  - 차량 이미지 (또는 "이미지 없음")
  - 상세 테이블: ID / 번호판 / 유형 / 속도 / 위치 / 상태 / 감지 시각
  - 미처리 건: "승인"/"반려" 버튼 → `PUT /enforcement/violations/{id}/status`

### 6.7 플레이스홀더 화면

| 화면 | 현재 상태 | 예정 기능 |
|------|----------|----------|
| DashboardView | 제목만 표시 | 집계 KPI, 실시간 현황 |
| CctvView | 제목만 표시 | CCTV 스트리밍 (FastAPI 연동) |
| PredictiveView | 제목만 표시 | RUL 예측, 고장 모드 분류 시각화 |
| StatisticsView | 제목만 표시 | 데이터 분석 차트/표 |

---

## 7. 프론트↔백엔드 API 연동 현황

### 7.1 완전 연동 (프론트 호출 → 백엔드 DB 처리)

| 프론트 화면 | API | 백엔드 처리 |
|------------|-----|------------|
| LoginView | `POST /auth/login` | MemberMapper.findByLoginId → BCrypt 검증 → 세션 |
| LoginView | `POST /auth/logout` | session.invalidate() |
| SignupView | `GET /auth/check-username` | MemberMapper.countByLoginId |
| SignupView | `POST /auth/signup` | MemberService.signup → BCrypt 해시 → INSERT |
| FindAccountView | `POST /auth/find-id` | MemberMapper.findByNameAndEmail → 마스킹 |
| FindAccountView | `POST /auth/verify-reset` | MemberMapper.findByLoginIdAndEmail |
| FindAccountView | `POST /auth/reset-password` | MemberService.changePassword → BCrypt |
| MypageView | `GET /member/profile` | MemberMapper.findByLoginId |
| MypageView | `PUT /member/profile` | MemberMapper.updateMember |
| MypageView | `POST /member/change-password` | BCrypt 검증 → updatePassword |
| EnforcementView | `GET /enforcement/violations` | ViolationMapper.findAll (페이징+필터) |
| EnforcementView | `PUT /enforcement/violations/{id}/status` | ViolationMapper.updateStatus |

### 7.2 더미 데이터 연동 (프론트 호출 → 백엔드 하드코딩 응답)

| 프론트 화면 | API | 백엔드 처리 |
|------------|-----|------------|
| TrafficView | `GET /traffic/summary` | 하드코딩 JSON |
| TrafficView | `GET /traffic/intersections` | 서울 8개 교차로 하드코딩 |
| TrafficView | `GET /traffic/flow/{id}` | 06:00~20:00 15건 하드코딩 |
| TrafficView | `POST /traffic/intersections/{id}/signal` | 검증만 수행, 실제 변경 없음 |

### 7.3 FastAPI → Spring Boot 연동

| 방향 | API | 기능 |
|------|-----|------|
| FastAPI → Spring Boot | `POST /enforcement/webhook` | YOLO/OCR 위반 이벤트 수신 → violation_log INSERT |

- **데이터 흐름:** FastAPI가 CCTV 영상 분석 → 위반 감지 → webhook으로 Spring Boot에 전송
- **위반 유형 변환:** SPEEDING→과속, RED_LIGHT→신호위반, CENTER_LINE→중앙선 침범, LINE_CROSSING→차선 위반
- **중복 방지:** `ON CONFLICT (event_id) DO NOTHING`

---

## 8. UI/UX 디자인 패턴

### 8.1 컬러 시스템

| 용도 | 색상 | 적용 위치 |
|------|------|----------|
| Primary | `#1A6DCC` | 버튼, 활성 네비, 링크, 선택 항목 |
| Primary Dark | `#1457A8` | 호버 상태 |
| Primary Light | `#E8F1FB` | 배경, 뱃지 |
| Success | `#10B981` | 승인, 정상, 통과 표시 |
| Warning | `#F59E0B` | 주의, 대기 상태 |
| Danger | `#EF4444` | 긴급, 반려, 에러 |
| Background | `#F4F6FA` | 페이지 배경 |
| Surface | `#FFFFFF` | 카드 배경 |
| Text Primary | `#1A1A2E` | 본문 텍스트 |
| Text Secondary | `#6B7280` | 보조 텍스트 |
| Border | `#E2E8F0` | 구분선, 입력 필드 테두리 |

### 8.2 공통 컴포넌트 패턴

- **카드:** 흰색 배경, border-radius 8~12px, 미세한 그림자
- **버튼:** Primary(파랑)/Secondary(회색), 호버 시 opacity 0.88, 클릭 시 scale 0.98
- **폼 입력:** 배경 `#ECECEE`, 포커스 시 파란 테두리 + 흰 배경
- **상태 뱃지:** 색상 코딩 (초록/노랑/빨강)
- **에러 처리:** 인라인 빨간 메시지 + shake 애니메이션
- **성공 처리:** 초록 메시지, 3초 후 자동 소멸

### 8.3 레이아웃 구조 (MainLayout)

```
┌──────────────── Header ────────────────┐
│ [Logo]                  [Logout][Mypage]│
├──────────────── Sidebar ───────────────┤
│ 메인 | 교통/신호 | CCTV | 단속 | 예지보전 | 통계 │
├────┬─────────────────────────┬─────────┤
│좌측│      Main Content       │  우측   │
│패널│   (max-width: 1280px)   │  패널   │
│0px │   padding: 24px 32px    │  0px    │
│    │   background: #F4F6FA   │         │
├────┴─────────────────────────┴─────────┤
│             Footer                      │
│ [팀원 이름] [기업 로고 4개] [AI-Pass]   │
└─────────────────────────────────────────┘
```

---

## 9. 보안 분석

### 9.1 구현된 보안 사항

| 항목 | 상태 | 설명 |
|------|------|------|
| 비밀번호 해싱 | ✅ | BCrypt (Spring Security Crypto) |
| 세션 HTTP-only | ✅ | JavaScript로 쿠키 접근 불가 |
| SameSite 쿠키 | ✅ | Lax 모드 (CSRF 기본 방어) |
| 인터셉터 인증 | ✅ | /api/** 전체 세션 검증 |
| 비밀번호 복잡성 | ✅ | 8~16자, 대/소문자+숫자+특수문자 |
| 중복 이벤트 방지 | ✅ | ON CONFLICT DO NOTHING |
| CORS preflight | ✅ | OPTIONS 요청 통과 처리 |
| 입력 검증 | ✅ | 프론트+백엔드 양쪽 검증 |

### 9.2 잠재 개선 사항

| 항목 | 현재 상태 | 권장 |
|------|----------|------|
| CORS origin | 모든 origin 허용 (`*`) | 운영 시 특정 도메인만 허용 |
| Webhook 인증 | 인증 없음 | API 키 또는 토큰 기반 인증 추가 |
| Rate limiting | 미구현 | 로그인 시도 제한 필요 |
| CSRF 토큰 | SameSite만 의존 | 명시적 CSRF 토큰 고려 |

---

## 10. 유효성 검증 규칙 정리

### 회원가입/비밀번호

| 필드 | 규칙 | 프론트 | 백엔드 |
|------|------|--------|--------|
| 아이디 | 4자 이상 | ✅ | ✅ |
| 비밀번호 | 8~16자 | ✅ | ✅ |
| 비밀번호 | 대문자 포함 | ✅ | ✅ (`.*[A-Z].*`) |
| 비밀번호 | 소문자 포함 | ✅ | ✅ (`.*[a-z].*`) |
| 비밀번호 | 숫자 포함 | ✅ | ✅ (`.*[0-9].*`) |
| 비밀번호 | 특수문자 포함 | ✅ | ✅ |
| 이름 | 2자 이상, 한글/영문 | ✅ | ✅ (`^[가-힣a-zA-Z]{2,}$`) |
| 이메일 | 이메일 형식 | ✅ | ✅ (`^[^\s@]+@[^\s@]+\.[^\s@]{2,}$`) |

### 신호 제어

| 필드 | 규칙 |
|------|------|
| 초록 신호 | 10~120초 |
| 노랑 신호 | 3~10초 (프론트), 미검증 (백엔드) |
| 빨강 신호 | 10~120초 |

---

## 11. 데이터 흐름 다이어그램

### 11.1 로그인 플로우

```
[사용자] → LoginView (username, password)
  → POST /api/auth/login
    → AuthController.login()
      → MemberService.findByLoginId()
        → MemberMapper.findByLoginId() → SQL: SELECT FROM member
      → BCrypt.matches(password, hashed)
      → session.setAttribute("loginMember", memberDTO)
    ← LoginResponse { username, name }
  → Pinia auth.user = response
  → router.push("/")
```

### 11.2 단속 이벤트 플로우

```
[CCTV 영상] → FastAPI (YOLO 감지 + OCR 번호판)
  → POST /api/enforcement/webhook
    → EnforcementController.handleWebhook()
      → 위반유형 영→한 변환
      → ViolationMapper.insert() → SQL: INSERT INTO violation_log (ON CONFLICT DO NOTHING)
    ← { success: true }

[관리자] → EnforcementView (필터/검색/페이징)
  → GET /api/enforcement/violations?plateNumber=&violationType=&status=&page=1&size=10
    → EnforcementController.getViolations()
      → ViolationMapper.findAll() + countAll()
    ← { items: [...], total, page, size, totalPages }

[관리자] → 상태 변경 (승인/반려)
  → PUT /api/enforcement/violations/{id}/status
    → ViolationMapper.updateStatus()
    ← { success: true, message: "상태가 변경되었습니다." }
```

---

## 12. 개발 진행 현황 요약

### 12.1 완성도 매트릭스

| 기능 영역 | 프론트엔드 | 백엔드 API | DB 연동 | 전체 |
|-----------|-----------|-----------|---------|------|
| 로그인 | ✅ 100% | ✅ 100% | ✅ | ✅ 완성 |
| 회원가입 | ✅ 100% | ✅ 100% | ✅ | ✅ 완성 |
| 계정찾기 | ✅ 100% | ✅ 100% | ✅ | ✅ 완성 |
| 마이페이지 | ✅ 100% | ✅ 100% | ✅ | ✅ 완성 |
| 교통/신호 제어 | ✅ 100% | ⚠️ 더미 | ❌ | ⚠️ 70% |
| 단속 내역 | ✅ 100% | ✅ 100% | ✅ | ✅ 완성 |
| CCTV | ❌ 0% | ❌ 0% | ❌ | ❌ 미착수 |
| 대시보드 | ❌ 0% | ❌ 0% | ❌ | ❌ 미착수 |
| 예지보전 | ❌ 0% | ❌ 0% | ❌ | ❌ 미착수 |
| 통계 | ❌ 0% | ❌ 0% | ❌ | ❌ 미착수 |

### 12.2 백엔드 DB 연동 vs 더미 현황

- **실제 DB 연동:** Auth (8개) + Member (3개) + Enforcement (4개) = **15개 엔드포인트**
- **더미 데이터:** Traffic (5개) = **5개 엔드포인트**
- **미구현:** CCTV, Dashboard, Predictive, Statistics = **0개 엔드포인트**

### 12.3 남은 작업 (코드 분석 기반)

| 우선순위 | 작업 | 관련 화면 |
|---------|------|----------|
| 🔴 높음 | Traffic DB 테이블 설계 + 더미→실제 전환 | TrafficView |
| 🔴 높음 | CCTV 스트리밍 연동 (FastAPI) | CctvView |
| 🔴 높음 | 예지보전 화면 개발 + ML API 연동 | PredictiveView |
| 🔴 높음 | 대시보드 KPI/현황 집계 | DashboardView |
| 🟡 중간 | 통계 화면 개발 (Chart.js 활용) | StatisticsView |
| 🟡 중간 | ITS API 실시간 교통 데이터 수집 | Traffic/Dashboard |
| 🟢 낮음 | CORS origin 제한 (운영 환경) | 전체 |
| 🟢 낮음 | Webhook 인증 추가 | EnforcementController |

---

## 13. 기술적 특이사항

1. **Spring Boot 4.0.3** — 최신 버전 사용 (Java 17 기반)
2. **MyBatis XML 위치** — `src/main/resources/sqls/` (일반적인 resources/mapper와 다름)
3. **camelCase↔snake_case 자동 매핑** — DatabaseConfig에서 설정
4. **Vite 프록시** — 개발 시 `/api` → `localhost:9000` 프록시로 CORS 우회
5. **좌우 패널** — MainLayout에 좌/우측 패널 영역이 존재하나 현재 width: 0px (향후 사이드바용)
6. **ViolationDTO.getStatus()** — DB 상태코드(UNPROCESSED/APPROVED/REJECTED)를 한글(대기중/승인/반려)로 변환하는 메서드 포함
7. **Chart.js 메모리 관리** — TrafficView에서 컴포넌트 언마운트 시 차트 인스턴스 destroy 처리
8. **Lazy loading** — 모든 라우트 컴포넌트가 동적 임포트로 코드 스플리팅 적용

---
---

# [하재영 담당 심층 분석] 2026-03-20 업데이트

> 하재영 담당 영역: 프론트엔드 전체 + 예지보전 AI(ML) + Spring Boot 백엔드 전체
> 추가 인수: 오종석 이탈로 공용화면, 로그인, 회원가입, 마이페이지, 교통신호 제어, CCTV 백엔드 전부 인수

---

## 14. FastAPI AI 서버 전체 분석

### 14.1 프로젝트 구조

```
AIpassFastAPI/
├── main.py                    FastAPI 앱 + 시작/종료 시퀀스
├── core/
│   ├── config.py              Pydantic Settings (env 기반)
│   └── hardware.py            GPU/CPU 가속 점검
├── api/
│   └── stream.py              스트리밍 + 상태 + 위반 캐시 라우터
├── services/
│   ├── vision.py              YOLO 멀티프로세스 엔진 (A/B/C)
│   ├── speed_detector.py      호모그래피 속도 감지
│   ├── aggregator.py          혼잡도 실시간 집계
│   ├── ocr_storage.py         PaddleOCR + 이미지 저장
│   └── webhook_client.py      Spring Boot 위반 전송 + DLQ
├── utils/
│   └── http_client.py         Async HTTP + Retry Queue
├── ml/
│   ├── config.py              9피처 스키마 + 하이퍼파라미터
│   ├── preprocess_9feat.py    KAIST/XJTU-SY 전처리
│   ├── train_rul.py           RUL XGBoost 회귀 학습
│   ├── train_failure_mode.py  고장모드 XGBoost 분류 학습
│   ├── train.py               학습 파이프라인 (CLI)
│   ├── validate.py            검증 스크립트
│   ├── weather_api.py         기상청 API 클라이언트
│   └── models/                학습된 모델 파일들
│       ├── rul_xgboost.json        (370KB)
│       ├── failure_mode_model.json  (602KB)
│       ├── scaler_rul.pkl
│       ├── scaler_fm.pkl
│       ├── label_encoder.pkl
│       ├── rul_feature_cols.pkl
│       └── fm_feature_cols.pkl
└── data/
    └── fallback_queue.jsonl   DLQ 미전송 데이터
```

### 14.2 멀티프로세스 아키텍처

```
[main.py lifespan 시작]
  │
  ├─ 1. 하드웨어 점검 (GPU/CPU)
  ├─ 2. http_client 시작 (Retry Queue, max 1000건)
  ├─ 2.5. Spring Boot GET /api/cctv/ai-target 호출 → CCTV URL 동적 적용
  │        (실패 시 .env VIDEO_SOURCE_URL fallback)
  ├─ 3. VisionEngine.start()
  │   ├─ Process A (video_reader_worker): RTSP/파일 캡처 → SharedMemory (10FPS)
  │   └─ Process B (ai_inference_worker): YOLO26n + ByteTrack → MJPEG 인코딩
  │       └─ SpeedDetector: 호모그래피 변환, EMA 평활화, 제한속도 50km/h
  │       └─ 이벤트 → event_queue로 발행
  ├─ 4. event_worker (asyncio task = Process C)
  │   └─ event_queue 소비 → 혼잡도/위반/긴급차량 처리
  └─ 5. start_aggregators() → 30초 주기 혼잡도 로깅
```

### 14.3 FastAPI 엔드포인트 전체 목록

| Method | 경로 | 기능 | 상태 |
|--------|------|------|------|
| GET | `/health` | 서버 상태 | ✅ |
| GET | `/api/v1/stream/video` | MJPEG 실시간 스트리밍 | ✅ |
| POST | `/api/v1/stream/source` | 동영상 소스 URL 변경 + 엔진 재시작 | ✅ |
| GET | `/api/v1/stream/status` | 엔진 상태 + 혼잡도 JSON | ✅ |
| GET | `/api/v1/stream/violations` | 최근 과속 위반 캐시 (max 100건) | ✅ |
| POST | `/api/v1/test/trigger-violation` | Postman 테스트용 OCR 강제 실행 | ✅ |
| POST | `/predict/rul` | RUL 예측 서빙 | ❌ **미구현** |
| POST | `/predict/failure-mode` | 고장모드 분류 서빙 | ❌ **미구현** |

### 14.4 FastAPI → Spring Boot 통신 상세

| FastAPI 발신 | Spring Boot 수신 | 클라이언트 | 상태 |
|-------------|-----------------|-----------|------|
| `POST /api/enforcement/webhook` | EnforcementController ✅ | webhook_client.py | ✅ 양쪽 완성 |
| `POST /api/traffic/count` | ❌ 미구현 | http_client.py | ⚠️ 발신만 |
| `POST /api/v1/vision/events` | ❌ 미구현 | http_client.py | ⚠️ 발신만 |
| `POST /api/v1/emergencies` | ❌ 미구현 | http_client.py | ⚠️ 발신만 |
| `GET /api/cctv/ai-target` (startup) | ❌ 미구현 | main.py httpx | ⚠️ 호출만 |

**핵심 문제:** FastAPI는 데이터를 보내지만, Spring Boot에 수신 엔드포인트가 없어서 http_client의 Retry Queue에 계속 쌓임

### 14.5 WebhookClient DLQ (Dead Letter Queue)

```
webhook_client.py 동작:
1. send_violation(payload) → POST /api/enforcement/webhook
2. 성공 → 로그 기록
3. 실패 → data/fallback_queue.jsonl에 JSONL 형태로 저장
4. retry_failed_payloads() → Read-Clear-Append 패턴으로 재전송
   - Lock으로 파일 I/O 정합성 보장
   - 재전송 실패 시 다시 파일에 보관
```

### 14.6 혼잡도 집계 엔진 (CongestionEngine)

```python
# aggregator.py
THRESHOLD_SMOOTH = 5    # 0~5대: SMOOTH (원활)
THRESHOLD_SLOW = 15     # 6~15대: SLOW (서행)
# 16대+: CONGESTED (혼잡)

# record_entry(track_id) → active_vehicles에 추가
# record_exit(track_id)  → active_vehicles에서 제거
# get_status() → { active_vehicles, congestion_level, total_entries, total_exits }
# 30초마다 자동 로깅
```

---

## 15. 예지보전 ML 모델 심층 분석

### 15.1 학습 파이프라인 구조

```
실행: python -m ml.train [옵션]
  --rul-only    RUL만 학습
  --cls-only    분류만 학습
  --use-rf      RandomForest 사용 (기본: XGBoost)

파이프라인:
1. preprocess_9feat.py → KAIST/XJTU-SY 원시 데이터 → 9피처 CSV
2. train_rul.py → rul_dataset_9feat.csv → XGBoost Regressor → rul_xgboost.json
3. train_failure_mode.py → failure_mode_dataset_9feat.csv → XGBoost Classifier → failure_mode_model.json
4. train.py → 리포트 생성 + 모델 백업 (타임스탬프)
5. validate.py → 테스트셋 검증
```

### 15.2 9개 센서 피처 상세

```python
FEATURE_COLUMNS_9 = [
    "vibration_rms",     # 진동 RMS (g) - 원시 신호 25,600Hz에서 계산
    "temperature",       # 기기 온도 (°C)
    "temp_residual",     # 온도 잔차 = temperature - (ambient_temp + 35.0)
    "motor_current",     # 모터 전류 (A) - 학습 시 더미값
    "operating_hours",   # 누적 가동 시간 (h) ← 피처 중요도 1위 (RUL)
    "ambient_temp",      # 외기 온도 (°C) - 기상청 KMA API
    "wind_speed",        # 풍속 (m/s) - 기상청 API
    "humidity",          # 습도 (%) - 기상청 API
    "season",            # 계절 (0=봄, 1=여름, 2=가을, 3=겨울)
]
```

**ExpectedTemp 공식:** `ExpectedTemp = ambient_temp + 35.0` (평균 발열값)
**temp_residual 공식:** `temp_residual = temperature - ExpectedTemp`

### 15.3 RUL 모델 성능

| 지표 | Train | Test | 판정 |
|------|-------|------|------|
| MAE | 0.03일 | 0.07일 | 양호 |
| RMSE | 0.05일 | 0.10일 | 양호 |
| R2 | 0.9998 | 0.9956 | **매우 우수** |
| CV MAE | - | 0.57일(±0.19) | 안정적 |
| 과적합 갭(R2) | - | 0.0042 | **최소** |

**피처 중요도 TOP 5:**
1. operating_hours: 0.6111
2. temperature: 0.2700
3. temp_residual: 0.0863
4. vibration_rms: 0.0145
5. humidity: 0.0071

### 15.4 고장모드 분류 모델 성능

| 지표 | Train | Test | 판정 |
|------|-------|------|------|
| Accuracy | 98.72% | 96.85% | **우수** |
| F1-Score | 0.9872 | 0.9685 | **우수** |
| ROC-AUC | - | 0.9967 | **최우수** |
| CV F1 | - | 0.4738(±0.17) | 변동 있음 |
| 과적합 갭(Acc) | - | 0.0187 | **최소** |

**클래스별 성능:**
| 클래스 | Precision | Recall |
|--------|-----------|--------|
| bearing_wear | 96.5% | 96.4% |
| motor_overheat | 97.3% | 97.2% |

**XJTU-SY 원본 고장모드 → PTZ 카메라 매핑:**
- outer_race → bearing_wear (베어링 마모)
- inner_race → motor_overheat (모터 과열)
- cage → bearing_wear
- outer_race_inner_race → bearing_wear
- inner_race_outer_race_cage → motor_overheat

### 15.5 RUL 위험도 등급

| 등급 | RUL 범위 | 색상 | 프론트엔드 표시 |
|------|---------|------|---------------|
| CRITICAL | 0~2일 | `#EF4444` | 빨강 경고 + 즉시 교체 |
| HIGH | 3~15일 | `#F59E0B` | 주황 경고 + 긴급 점검 |
| MEDIUM | 16~30일 | `#FB923C` | 노랑 주의 + 계획 정비 |
| LOW | 31일+ | `#10B981` | 초록 정상 |

### 15.6 ML 서빙 엔드포인트 구현 계획

**현재:** 모델 학습/저장 완료, 서빙 코드 미작성

**구현 필요:**
```python
# FastAPI에 추가할 엔드포인트

@app.post("/predict/rul")
async def predict_rul(data: SensorInput):
    # 1. 9개 피처 추출
    # 2. scaler_rul.pkl로 스케일링
    # 3. rul_xgboost.json 모델 predict
    # 4. RUL일수 → 위험도 등급 매핑
    return { "rul_days": float, "risk_level": str, "confidence": float }

@app.post("/predict/failure-mode")
async def predict_failure_mode(data: SensorInput):
    # 1. 9개 피처 추출
    # 2. scaler_fm.pkl로 스케일링
    # 3. failure_mode_model.json predict_proba
    # 4. label_encoder.pkl로 디코딩
    return { "failure_mode": str, "confidence": float, "probabilities": dict }
```

---

## 16. DB 스키마 & 백엔드 갭 분석

### 16.1 DB 8개 테이블 vs 백엔드 구현 현황

```
DB 테이블                    DAO              SQL XML         Service          Controller
─────────────────────────────────────────────────────────────────────────────────────────
member              ✅ MemberMapper     ✅ member.xml    ✅ MemberService  ✅ Auth+Member
violation_log       ✅ ViolationMapper  ✅ violation.xml  ⚠️ 컨트롤러 직접   ✅ Enforcement
intersection        ❌ 없음             ❌ 없음           ❌ 없음           ⚠️ Traffic(더미)
equipment           ❌ 없음             ❌ 없음           ❌ 없음           ❌ 없음
sensor_log          ❌ 없음             ❌ 없음           ❌ 없음           ❌ 없음
traffic_congestion  ❌ 없음             ❌ 없음           ❌ 없음           ❌ 없음
signal_control_log  ❌ 없음             ❌ 없음           ❌ 없음           ❌ 없음
maintenance_log     ❌ 없음             ❌ 없음           ❌ 없음           ❌ 없음
```

**결론: 8개 테이블 중 2개만 백엔드 연동 완료, 6개 테이블의 전체 레이어 구현 필요**

### 16.2 테이블별 필요 구현 상세

#### intersection (교차로)

```sql
-- 이미 생성됨
intersection_id BIGSERIAL PK
name VARCHAR(100) NOT NULL
latitude DECIMAL(10,8)
longitude DECIMAL(11,8)
created_at TIMESTAMP
```

필요한 DAO 메서드:
- `findAll()` → 전체 교차로 목록
- `findById(Long id)` → 단건 조회
- `findWithLatestCongestion()` → 교차로 + 최신 혼잡도 JOIN

#### equipment (장비)

```sql
equipment_id BIGSERIAL PK
intersection_id BIGINT FK → intersection
equipment_type VARCHAR(50) NOT NULL  -- 'PTZ_MOTOR', 'COOLING_FAN'
status VARCHAR(20) DEFAULT 'NORMAL'  -- 'NORMAL', 'WARNING', 'CRITICAL'
installation_date DATE
created_at TIMESTAMP
```

필요한 DAO 메서드:
- `findAll()` → 장비 전체 목록
- `findByIntersectionId(Long id)` → 교차로별 장비
- `findById(Long id)` → 단건
- `findWithLatestSensor()` → 장비 + 최신 센서값 JOIN
- `updateStatus(Long id, String status)` → AI가 상태 변경

#### sensor_log (센서 데이터)

```sql
log_id BIGSERIAL PK
equipment_id BIGINT FK → equipment
temperature DECIMAL(6,2)
vibration DECIMAL(6,2)
risk_score DECIMAL(3,2)  -- 0.00~1.00
recorded_at TIMESTAMP
```

필요한 DAO 메서드:
- `findLatestByEquipmentId(Long equipmentId)` → 최신 1건
- `findHistoryByEquipmentId(Long equipmentId, String from, String to)` → 시계열 데이터
- `insert(SensorLogDTO dto)` → 센서값 기록
- `countByRiskScoreAbove(Double threshold)` → 위험 장비 수 집계

#### traffic_congestion (혼잡도)

```sql
congestion_id BIGSERIAL PK
intersection_id BIGINT FK → intersection
vehicle_count INT DEFAULT 0
congestion_level VARCHAR(20)  -- 'SMOOTH', 'SLOW', 'CONGESTED'
recorded_at TIMESTAMP
```

필요한 DAO 메서드:
- `findLatestByIntersectionId(Long id)` → 최신 혼잡도
- `findByDateRange(Long intersectionId, String from, String to)` → 시간대별 통계
- `insert(TrafficCongestionDTO dto)` → FastAPI에서 수신한 혼잡도 저장
- `getSummary()` → 전체 교차로 혼잡도 요약

#### signal_control_log (신호 제어 이력)

```sql
control_id BIGSERIAL PK
intersection_id BIGINT FK → intersection
control_type VARCHAR(50)     -- 'AUTO_EMERGENCY', 'MANUAL'
control_reason VARCHAR(255)  -- "구급차 북측 진입 녹색불 전환"
created_at TIMESTAMP
```

필요한 DAO 메서드:
- `insert(SignalControlDTO dto)` → 제어 이력 기록
- `findByIntersectionId(Long id)` → 교차로별 제어 이력
- `findRecent(int limit)` → 최근 N건 (대시보드 알림용)

#### maintenance_log (수리 티켓)

```sql
ticket_id BIGSERIAL PK
equipment_id BIGINT FK → equipment
repair_status VARCHAR(20) DEFAULT 'REQUESTED'  -- REQUESTED/IN_PROGRESS/COMPLETED
reported_by VARCHAR(50)
created_at TIMESTAMP
resolved_at TIMESTAMP (nullable)
```

필요한 DAO 메서드:
- `insert(MaintenanceDTO dto)` → 수리 요청 생성
- `findAll()` → 전체 티켓 목록
- `findByEquipmentId(Long id)` → 장비별 수리 이력
- `updateStatus(Long ticketId, String status, Timestamp resolvedAt)` → 상태 변경
- `countByStatus(String status)` → 상태별 건수 (대시보드용)

---

## 17. 미구현 화면별 필요 API 설계

### 17.1 Dashboard (대시보드) API

| Method | 경로 | 기능 | 데이터 소스 |
|--------|------|------|-----------|
| GET | `/api/dashboard/kpi` | 오늘 KPI 요약 | violation_log COUNT + traffic_congestion SUM + equipment 상태 집계 |
| GET | `/api/dashboard/alerts` | 최근 알림 목록 | signal_control_log 최근 + sensor_log (risk_score > 0.7) |
| GET | `/api/dashboard/congestion` | 교차로별 실시간 혼잡도 | intersection JOIN traffic_congestion (최신) |
| GET | `/api/dashboard/violations-today` | 오늘 단속 건수 추이 | violation_log 시간별 GROUP BY |

### 17.2 CCTV API

| Method | 경로 | 기능 | 비고 |
|--------|------|------|------|
| GET | `/api/cctv/list` | 카메라 목록 | equipment WHERE type='CAMERA' |
| GET | `/api/cctv/ai-target` | AI 분석 대상 URL | **FastAPI startup에서 호출 중** |
| POST | `/api/cctv/ai-target` | AI 분석 대상 변경 | FastAPI /api/v1/stream/source 연동 |

**프론트엔드 CCTV 스트리밍:** `<img src="http://localhost:FASTAPI_PORT/api/v1/stream/video">` 직접 연결

### 17.3 Predictive (예지보전) API

| Method | 경로 | 기능 |
|--------|------|------|
| GET | `/api/predictive/equipment` | 장비 목록 + 최신 센서값 + 상태 |
| GET | `/api/predictive/equipment/{id}` | 장비 상세 + 센서 시계열 |
| GET | `/api/predictive/equipment/{id}/rul` | RUL 예측 (FastAPI 호출 또는 캐시) |
| GET | `/api/predictive/equipment/{id}/failure-mode` | 고장모드 분류 |
| POST | `/api/predictive/maintenance` | 수리 기사 호출 (maintenance_log INSERT) |
| GET | `/api/predictive/maintenance` | 수리 티켓 목록 |
| PUT | `/api/predictive/maintenance/{id}` | 수리 상태 변경 (REQUESTED→IN_PROGRESS→COMPLETED) |

### 17.4 Statistics (통계) API

| Method | 경로 | 기능 |
|--------|------|------|
| GET | `/api/statistics/violations/by-type` | 위반유형별 건수 (파이 차트) |
| GET | `/api/statistics/violations/by-date` | 일자별 위반 추이 (라인 차트) |
| GET | `/api/statistics/traffic/by-hour` | 시간대별 교통량 (막대 차트) |
| GET | `/api/statistics/traffic/by-intersection` | 교차로별 혼잡도 비교 |
| GET | `/api/statistics/equipment/status` | 장비 상태 분포 (도넛 차트) |

### 17.5 Traffic 수신 엔드포인트 (FastAPI → Spring Boot)

| Method | 경로 | 기능 | 현재 |
|--------|------|------|------|
| POST | `/api/traffic/count` | 2분 주기 혼잡도 수신 → traffic_congestion INSERT | ❌ 수신측 미구현 |
| POST | `/api/traffic/emergency` | 긴급차량 감지 → signal_control_log INSERT | ❌ 수신측 미구현 |

---

## 18. 시스템 간 데이터 흐름 전체 맵

### 18.1 단속 플로우 ✅ (완성)

```
CCTV 영상
  → [FastAPI Process A] RTSP 프레임 캡처 (10 FPS, SharedMemory)
    → [FastAPI Process B] YOLOv8 객체추적 (ByteTrack) + 속도감지 (호모그래피, >50km/h)
      → [FastAPI Process C] PaddleOCR 번호판 추출 + 이미지 저장
        → webhook_client.py → POST /api/enforcement/webhook
          → [Spring Boot] EnforcementController
            → ViolationMapper.insert() → violation_log (ON CONFLICT event_id DO NOTHING)
              → [Vue] EnforcementView 조회 → 관리자 승인/반려
```

### 18.2 교통 혼잡도 플로우 ⚠️ (절반)

```
[FastAPI Process B] ROI 내 차량 카운트
  → [CongestionEngine] 실시간 집계 (SMOOTH/SLOW/CONGESTED)
    → http_client.py → POST /api/traffic/count
      → [Spring Boot] ❌ 수신 엔드포인트 없음
        → traffic_congestion INSERT ❌
          → [Vue] TrafficView ❌ 더미 데이터 사용 중
```

### 18.3 예지보전 플로우 ❌ (미구현)

```
[센서 데이터] → sensor_log INSERT ❌ (수집 미구현)
  → [Spring Boot] 센서 조회 → [FastAPI] POST /predict/rul ❌ (서빙 미구현)
    → RUL 결과 + 고장모드 → equipment.status UPDATE ❌
      → [Vue] PredictiveView ❌ (화면 미구현)
        → 수리 기사 호출 → maintenance_log INSERT ❌
```

### 18.4 긴급차량 플로우 ⚠️ (감지만)

```
[FastAPI Process B] YOLO 긴급차량 감지 (class 9=구급차, 10=소방차)
  → http_client.py → POST /api/v1/emergencies
    → [Spring Boot] ❌ 수신 미구현
      → signal_control_log INSERT ❌
        → 자동 신호 제어 + [Vue] TrafficView 팝업 ❌
```

### 18.5 CCTV 스트리밍 플로우 ⚠️ (백엔드만)

```
[FastAPI] Process A+B → MJPEG 프레임 → mjpeg_queue
  → GET /api/v1/stream/video → multipart/x-mixed-replace 스트리밍
    → [Vue] CctvView <img src="..."> ❌ (화면 미구현)

[Spring Boot] GET /api/cctv/ai-target ❌ (엔드포인트 미구현)
  → [FastAPI] startup에서 호출하여 CCTV URL 동적 적용
```

---

## 19. 개발 우선순위 로드맵

### Phase 1: 백엔드 코어 레이어 구축 (예상 2~3일)

```
[1일차]
  1-1. DTO 생성: EquipmentDTO, SensorLogDTO, MaintenanceDTO, TrafficCongestionDTO, SignalControlDTO
  1-2. DAO 인터페이스: IntersectionMapper, EquipmentMapper, SensorLogMapper, MaintenanceMapper
  1-3. SQL XML: intersection.xml, equipment.xml, sensor_log.xml, maintenance.xml

[2일차]
  1-4. Service 생성: TrafficService, PredictiveService
  1-5. TrafficController 더미→DB 전환 (API 경로/응답 형식 유지, 내부만 교체)
  1-6. PredictiveController 신규 (장비목록/센서이력/수리티켓)

[3일차]
  1-7. FastAPI 수신 엔드포인트: POST /api/traffic/count, POST /api/traffic/emergency
  1-8. CctvController (GET /api/cctv/ai-target 등)
  1-9. DB 초기 데이터 INSERT (intersection 8개, equipment 샘플)
```

### Phase 2: FastAPI ML 서빙 (예상 1일)

```
  2-1. /predict/rul 엔드포인트 구현 (모델 로드→스케일링→예측→위험도)
  2-2. /predict/failure-mode 엔드포인트 구현
  2-3. Spring Boot에서 FastAPI ML 호출 Service (또는 Vite 프록시 추가)
```

### Phase 3: 프론트엔드 화면 구현 (예상 5~7일)

```
  3-1. CctvView: CCTV 목록 + MJPEG 뷰어 (1일)
  3-2. PredictiveView: 장비목록/RUL게이지/고장모드/센서차트/수리호출 (2일)
  3-3. DashboardView: KPI카드+알림+혼잡도현황 (2일)
  3-4. StatisticsView: Chart.js 다중 차트 (1~2일)
  3-5. TrafficView: 더미→실데이터 전환 확인 (0.5일)
```

### Phase 4: 통합 및 마무리 (예상 2~3일)

```
  4-1. 센서 데이터 시뮬레이터 (sensor_log 주기적 INSERT)
  4-2. 대시보드 실시간 갱신 (setInterval polling 또는 SSE)
  4-3. CCTV ↔ 교차로 연동 (교차로 선택→해당 CCTV 스트리밍)
  4-4. 전체 플로우 E2E 테스트
  4-5. UI 최종 다듬기 (iOS 느낌 일관성)
```

---

## 20. 최종 완성도 매트릭스 (업데이트)

| 기능 | FE | BE API | DB 연동 | FastAPI | ML 모델 | 전체 |
|------|----|----|----|----|----|----|
| 로그인/회원가입/계정찾기 | ✅ | ✅ | ✅ | - | - | **100%** |
| 마이페이지 | ✅ | ✅ | ✅ | - | - | **100%** |
| 단속 내역 | ✅ | ✅ | ✅ | ✅ webhook | - | **100%** |
| 교통/신호 제어 | ✅ | ⚠️ 더미 | ❌ | ⚠️ 혼잡도만 | - | **40%** |
| CCTV | ❌ | ❌ | ❌ | ✅ MJPEG | - | **25%** |
| 대시보드 | ❌ | ❌ | ❌ | - | - | **0%** |
| 설비 예지보전 | ❌ | ❌ | ❌ | ⚠️ 서빙 미구현 | ✅ 학습완료 | **20%** |
| 통계 | ❌ | ❌ | ❌ | - | - | **0%** |

**전체 프로젝트 진행률: 약 48%**
