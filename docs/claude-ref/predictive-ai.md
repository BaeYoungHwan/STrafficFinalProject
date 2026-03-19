# 예지보전 & 과속 감지 AI 참고

## 예지보전 ML 모델

| 모델 | 알고리즘 | 엔드포인트 |
|------|---------|-----------|
| RUL 예측 | XGBoost (회귀) | `POST /predict/rul` |
| 고장 모드 분류 | XGBoost or RandomForest | `POST /predict/failure-mode` |

- 학습 스크립트: `AIpassFastAPI/ml/`
- 진입점: `python -m ml` (ml/__main__.py)

### RUL 등급 기준

| 등급 | RUL 범위 | 표시 색상 |
|------|---------|----------|
| CRITICAL | 0~2일 | `#EF4444` |
| HIGH | 3~15일 | `#F59E0B` |
| MEDIUM | 16~30일 | `#FB923C` |
| LOW | 31일+ | `#10B981` |

- DB 저장: 마지막 갱신 RUL + 타임스탬프
- 표시값 계산: `저장 RUL − 경과 일수`
- `ExpectedTemp = ambient_temp + 장비 평균 발열값`
- 기온 소스: 기상청 KMA API → `ml/weather_api.py`

---

## 과속 감지 알고리즘 (speed_detector.py)

- **위치:** `AIpassFastAPI/services/speed_detector.py`
- **제한속도:** 50 km/h (`SPEED_LIMIT_KMH = 50.0`)

### 동작 방식
1. **호모그래피 변환** — 영상 픽셀 좌표 → 실세계 미터 좌표
   - `src_pts` (영상 4점) → `dst_pts` (실세계 10m × 30m 직사각형)
2. **트래킹 기준** — 타이어 접지면(`y_max = y_center + height/2`) 사용
3. **속도 계산** — 최근 15프레임 중 가장 오래된 점 → 최신 점의 `거리(m) / 시간(s) × 3.6`
4. **EMA 스무딩** — `alpha = 0.3` 지수이동평균으로 노이즈 제거
5. **과속 이벤트** — 50km/h 초과 & `is_reported == False`일 때 `event_queue`에 `WEBHOOK_VIOLATION` 적재 (멱등성 보장)
6. **GC** — 2초 이상 미감지 track_id 자동 삭제

### 스트림 오버레이
- 정상: 초록 텍스트 `"XX km/h"`
- 과속: 빨간 텍스트 `"XX km/h"`
- 단속선: 빨간 수평선 (`VIOLATION_LINE_Y = 600`)

### 위반 이벤트 페이로드 예시
```json
{
  "eventId": "EVT-20260319-120000-A1B2",
  "timestamp": "2026-03-19T12:00:00Z",
  "cameraLocation": "강화대교_메인_01",
  "violationType": "SPEEDING",
  "speedKmh": 72.3,
  "mockLprData": {
    "plateNumber": "123가4567",
    "confidence": 0.98
  }
}
```
