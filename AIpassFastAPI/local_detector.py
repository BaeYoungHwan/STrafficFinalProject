"""
local_detector.py - 로컬 과속 감지기 (OpenCV 창 방식)

실행:  cd AIpassFastAPI && python local_detector.py
종료:  OpenCV 창에서 'q' 키

[동작 방식]
- 메인 스레드: VideoCapture → YOLO → cv2.imshow (화면 렌더링 전담)
- 백그라운드 스레드: asyncio 루프 — OCR + 웹훅 전송 (렌더링 블로킹 없음)
- 위반 발생 시: run_coroutine_threadsafe()로 백그라운드 루프에 위임

[필요 설정 (.env)]
  LOCAL_DETECTOR_MODE=true    ← FastAPI VisionEngine 비활성화 (YOLO 중복 방지)
  VIDEO_SOURCE_URL=<영상URL>  ← RTSP 또는 로컬 파일 경로
"""

import asyncio
import glob as _glob
import logging
import os
import random
import sys
import threading
from datetime import datetime
from pathlib import Path

import cv2

# AIpassFastAPI 루트를 패키지 경로에 등록
sys.path.insert(0, str(Path(__file__).parent))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from ultralytics import YOLO

from core.config import settings
from services.ocr_storage import run_ocr_on_file
from services.speed_detector import (
    MAX_PLAUSIBLE_SPEED_KMH,
    SPEED_LIMIT_KMH,
    process_headless_inference,
    vehicle_history,
)
from services.webhook_client import WebhookClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── 백그라운드 asyncio 루프 (OCR + 웹훅 전용) ──────────────────────────────
_bg_loop = asyncio.new_event_loop()
_webhook = WebhookClient()


def _run_bg_loop() -> None:
    asyncio.set_event_loop(_bg_loop)
    _bg_loop.run_forever()


threading.Thread(target=_run_bg_loop, daemon=True, name="async-bg").start()

# httpx AsyncClient 초기화 (백그라운드 루프에서 실행)
asyncio.run_coroutine_threadsafe(_webhook.start(), _bg_loop).result(timeout=5)


# ─── carnumber 이미지 목록 ────────────────────────────────────────────────────
def _get_carnumber_images() -> list:
    return _glob.glob("data/carnumber/*.jpeg") + _glob.glob("data/carnumber/*.jpg")


# ─── 위반 처리 (백그라운드 루프에서 실행) ────────────────────────────────────
async def _handle_violation(payload: dict) -> None:
    """과속 이벤트: OCR → 웹훅 전송 (백그라운드 asyncio 루프 전용)"""
    payload["cameraId"] = settings.CAMERA_ID
    src_path = payload.pop("src_image_path", None)
    if src_path:
        payload["srcImageUrl"] = f"carnumber/{os.path.basename(src_path)}"

    if src_path and os.path.exists(src_path):
        result = await run_ocr_on_file(src_path)
        payload["plateNumber"] = result["plate_number"]
        payload["imageUrl"] = result["image_url"]
        payload["needsReview"] = result.get("needs_review", False)
        logger.info(
            "[OCR] %s | 검토필요: %s", result["plate_number"], result.get("needs_review")
        )
    else:
        payload["plateNumber"] = "미인식"
        payload["imageUrl"] = None
        logger.warning("[OCR] carnumber 이미지 없음 — 미인식 처리")

    await _webhook.send_violation(payload)


def _submit_violation(payload: dict) -> None:
    """메인 스레드에서 백그라운드 루프로 위반 처리 위임 (non-blocking)"""
    asyncio.run_coroutine_threadsafe(_handle_violation(payload), _bg_loop)


# ─── 속도 오버레이 ────────────────────────────────────────────────────────────
def _draw_speed_overlay(frame, results) -> None:
    """각 차량 bbox 위에 속도 텍스트 표시 (vision.py 로직 동일)"""
    if not (results[0].boxes and results[0].boxes.id is not None):
        return

    id_list = results[0].boxes.id.int().cpu().tolist()
    for i, track_id in enumerate(id_list):
        data = vehicle_history.get(track_id)
        if data is None:
            continue
        speed = min(
            data.get("ema_speed", 0.0) * settings.SPEED_SCALE_FACTOR,
            MAX_PLAUSIBLE_SPEED_KMH,
        )
        if speed < 50:
            continue
        box = results[0].boxes[i]
        x_c, y_c, w, _ = box.xywh[0].tolist()
        x_px = int(x_c - w / 2)
        y_px = max(0, int(y_c) - 10)
        if speed >= SPEED_LIMIT_KMH:
            color = (0, 0, 255)    # 빨강 — 과속
        elif speed >= 60:
            color = (0, 220, 0)    # 초록
        else:
            color = (255, 255, 255)  # 흰색
        cv2.putText(
            frame, f"ID:{track_id} {speed:.0f}km/h",
            (x_px, y_px), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA,
        )


# ─── 메인 감지 루프 ───────────────────────────────────────────────────────────
def main() -> None:
    carnumber_images = _get_carnumber_images()
    if not carnumber_images:
        logger.warning("[초기화] data/carnumber/ 이미지 없음 — OCR 없이 실행됩니다")

    logger.info("[초기화] YOLO 모델 로드: %s", settings.YOLO_MODEL)
    model = YOLO(settings.YOLO_MODEL)

    source = settings.VIDEO_SOURCE_URL
    if not source:
        logger.error("[초기화] VIDEO_SOURCE_URL이 .env에 설정되지 않았습니다")
        return

    logger.info("[초기화] 비디오 소스: %s", source)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        logger.error("[초기화] 비디오 소스 열기 실패: %s", source)
        return

    logger.info("로컬 감지기 시작 | OpenCV 창에서 'q' 키로 종료")

    frame_count = 0
    _last_results = None

    while True:
        ret, frame = cap.read()
        if not ret:
            logger.warning("프레임 읽기 실패 — 스트림 종료")
            break

        frame_count += 1
        # 2프레임에 1회만 YOLO 추론 (CPU 절감)
        _is_new = (frame_count % 2 != 0) or (_last_results is None)

        if _is_new:
            results = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                imgsz=settings.INFERENCE_IMGSZ,
                conf=settings.CONF_THRESHOLD,
                classes=settings.TARGET_CLASSES,
                verbose=False,
            )
            _last_results = results

            # 과속 감지 — 새 추론 결과일 때만 (재사용 프레임은 EMA 왜곡 방지)
            speeding_events = process_headless_inference(results)
            for evt in speeding_events:
                if carnumber_images:
                    evt["payload"]["src_image_path"] = random.choice(carnumber_images)
                logger.info("[과속] ID:%s %.1fkm/h", evt["track_id"], evt["speed"])
                _submit_violation(evt["payload"])
        else:
            results = _last_results

        # 시각화
        annotated = results[0].plot(labels=False)
        _draw_speed_overlay(annotated, results)

        # 상태 표시줄
        ts = datetime.now().strftime("%H:%M:%S")
        cv2.putText(
            annotated,
            f"AIpass Local | {ts} | 제한속도: {SPEED_LIMIT_KMH:.0f}km/h",
            (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2,
        )

        display = cv2.resize(annotated, (960, 540))
        cv2.imshow("AIpass - 로컬 과속 감지", display)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            logger.info("사용자 종료 요청")
            break

    cap.release()
    cv2.destroyAllWindows()

    # 백그라운드 루프 종료
    asyncio.run_coroutine_threadsafe(_webhook.stop(), _bg_loop).result(timeout=3)
    _bg_loop.call_soon_threadsafe(_bg_loop.stop)
    logger.info("로컬 감지기 종료 완료")


if __name__ == "__main__":
    main()
