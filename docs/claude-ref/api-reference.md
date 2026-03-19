# API 참고

## FastAPI 스트리밍 API (`http://localhost:8000`)

### `/api/v1/stream/`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/stream/video` | MJPEG 실시간 스트리밍 (`multipart/x-mixed-replace`) |
| POST | `/stream/source` | 동영상 소스 URL 변경 (body: `{"url": "..."}`) |
| GET | `/stream/status` | VisionEngine 상태 확인 |
| GET | `/stream/violations` | 최근 과속 위반 목록 (메모리 캐시, 최대 100건) |

### 기타

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |
| POST | `/api/v1/test/trigger-violation` | Postman 테스트용 강제 위반 처리 |

### Vue에서 MJPEG 표시
```html
<img src="http://localhost:8000/api/v1/stream/video" />
```

### 동영상 소스 설정 (.env)
```
VIDEO_SOURCE_URL=C:/path/to/video.mp4      # 로컬 파일
VIDEO_SOURCE_URL=rtsp://ip:port/stream      # RTSP
VIDEO_SOURCE_URL=http://example.com/video.mp4  # HTTP
```

---

## Spring Boot API (`http://localhost:9000`)

### 인증 (`/api/auth/`) — 세션 불필요

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/auth/login` | 로그인 (세션 생성) |
| POST | `/auth/logout` | 로그아웃 |
| GET | `/auth/check` | 세션 유효성 확인 |
| GET | `/auth/check-username` | ID 중복 확인 |
| POST | `/auth/find-id` | ID 찾기 (name + email) |
| POST | `/auth/verify-reset` | 비밀번호 재설정 인증 |
| POST | `/auth/reset-password` | 비밀번호 재설정 |
| POST | `/auth/signup` | 회원가입 |

### 회원 (`/api/member/`) — 세션 필요

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/member/profile` | 프로필 조회 |
| PUT | `/member/profile` | 프로필 수정 |
| POST | `/member/change-password` | 비밀번호 변경 |

### 교통 (`/api/traffic/`) — 세션 필요 (현재 더미 데이터)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/traffic/intersections` | 교차로 목록 (8개) |
| GET | `/traffic/intersections/{id}` | 교차로 단건 |
| GET | `/traffic/flow/{intersectionId}` | 교통량 데이터 (15시간) |
| GET | `/traffic/summary` | 요약 통계 |
| POST | `/traffic/intersections/{id}/signal` | 신호 타이밍 수정 |

### API 응답 형식
```json
{ "success": true, "data": {}, "message": "" }
```
