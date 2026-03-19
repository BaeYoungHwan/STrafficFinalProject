# 구현 현황 참고

## Frontend View 구현 상태

| View | 경로 | 상태 | 비고 |
|------|------|------|------|
| LoginView | /login | ✅ 완료 | 폼 검증, 에러 메시지 |
| SignupView | /signup | ✅ 완료 | shake 애니메이션, ID 중복체크 |
| FindAccountView | /find-account | ✅ 완료 | 멀티스텝 (ID찾기 / 비번재설정) |
| DashboardView | / | 🔲 플레이스홀더 | 개발 예정 |
| MypageView | /mypage | ✅ 완료 | 프로필 수정 + 비밀번호 변경 |
| TrafficView | /traffic | ✅ 완료 | 교차로 목록 + 신호 제어 패널 |
| CctvView | /cctv | 🔲 플레이스홀더 | MJPEG 스트리밍 연동 예정 |
| EnforcementView | /enforcement | 🔲 플레이스홀더 | 개발 예정 |
| PredictiveView | /predictive | 🔲 플레이스홀더 | 개발 예정 |
| StatisticsView | /statistics | 🔲 플레이스홀더 | 개발 예정 |

## Backend API 구현 상태

| 모듈 | 파일 | 상태 |
|------|------|------|
| 인증 | AuthController.java | ✅ 완료 (로그인/회원가입/찾기/재설정) |
| 회원 | MemberController.java | ✅ 완료 (프로필/비번 변경) |
| 교통 | TrafficController.java | ⚠️ 더미 데이터 (DB 연동 미완) |
| CCTV | — | 🔲 미구현 |
| 단속 | — | 🔲 미구현 |
| 예지보전 | — | 🔲 미구현 |
| 통계 | — | 🔲 미구현 |

## FastAPI 구현 상태

| 파일 | 상태 | 비고 |
|------|------|------|
| main.py | ✅ 완료 | lifespan 관리 |
| services/vision.py | ✅ 완료 | YOLO + 과속 감지 + MJPEG |
| services/speed_detector.py | ✅ 완료 | 호모그래피 + EMA |
| services/aggregator.py | ✅ 완료 | CongestionEngine |
| services/ocr_storage.py | ✅ 완료 | PaddleOCR |
| services/webhook_client.py | ✅ 완료 | DLQ 패턴 |
| api/stream.py | ✅ 완료 | MJPEG 스트리밍 엔드포인트 |
| utils/http_client.py | ✅ 완료 | retry queue |
| ml/ (학습 스크립트) | ✅ 완료 | RUL + 고장 모드 |
| predict 엔드포인트 | 🔲 미구현 | /predict/rul, /predict/failure-mode |
