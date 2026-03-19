# TODO - 2026-03-19

---

## 📊 전체 진척도

```
전체       ████████████░░░░░░░░  58%   (15 / 26)

Frontend   ██████████░░░░░░░░░░  50%   (5 / 10)
  ✅ Login / Signup / FindAccount / Mypage / Traffic
  🔲 Dashboard / CCTV / Enforcement / Predictive / Statistics

Backend    █████████░░░░░░░░░░░  43%   (3 / 7)
  ✅ Auth / Member
  ⚠️ Traffic (더미 데이터)
  🔲 CCTV / Enforcement / Predictive / Statistics

FastAPI    ██████████████████░░  89%   (8 / 9)
  ✅ VisionEngine / SpeedDetector / Aggregator
  ✅ OCR / Webhook / Stream / HttpClient / ML
  🔲 Predict 엔드포인트 (/predict/rul, /predict/failure-mode)
```

> 기준: `docs/claude-ref/implementation-status.md`

---

## 오늘 할 일
- [x] 프로젝트 전체 학습 (코드베이스 전체 탐색 완료)
- [x] CLAUDE.md 완벽 작성 (현재 구현 상태, DB 스키마, 미구현 파일, 과속 알고리즘 등 보완)
- [x] FastAPI 과속 감지 실시간 스트리밍 서버 구축
  - [x] `api/__init__.py`, `utils/__init__.py` 생성
  - [x] `utils/http_client.py` — Spring Boot 연동 HTTP 클라이언트 (retry queue)
  - [x] `services/aggregator.py` — CongestionEngine + 백그라운드 모니터
  - [x] `api/stream.py` — MJPEG 스트리밍 + 소스 변경 + 위반 목록 엔드포인트
  - [x] `services/vision.py` 수정 — speed_detector 연동 + 속도 오버레이 + restart()
  - [x] `core/config.py` 수정 — VIDEO_SOURCE_URL 추가, BACKEND_URL 포트 수정(8080→9000)

## 완료
- [x] 프로젝트 전체 학습
- [x] CLAUDE.md 완벽 작성
- [x] FastAPI 과속 감지 실시간 스트리밍 서버 구축
