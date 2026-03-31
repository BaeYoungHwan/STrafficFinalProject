"""YOLO 기반 번호판 영역 검출기"""
import os
import logging
import numpy as np
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_plate_model = None
_model_load_failed = False

# __file__ 기준 상대경로 — 절대경로 하드코딩 금지
_LOCAL_MODEL_PATH = Path(__file__).parent / "plate_yolo.pt"
_REMOTE_MODEL_ID  = "keremberke/yolov8n-license-plate-detection"


def _get_plate_model():
    global _plate_model, _model_load_failed
    if _model_load_failed:
        return None
    if _plate_model is not None:
        return _plate_model
    try:
        from ultralytics import YOLO
        if _LOCAL_MODEL_PATH.exists():
            _plate_model = YOLO(str(_LOCAL_MODEL_PATH))
            logger.info("[PlateDetector] 로컬 학습 모델 로드: %s", _LOCAL_MODEL_PATH)
        else:
            _plate_model = YOLO(_REMOTE_MODEL_ID)
            logger.info("[PlateDetector] HuggingFace 모델 로드: %s", _REMOTE_MODEL_ID)
        return _plate_model
    except Exception as e:
        logger.warning("[PlateDetector] 모델 로드 실패 — OCR 파이프라인으로 폴백: %s", e)
        _model_load_failed = True
        return None


def detect_plate_crop(frame: np.ndarray, conf_threshold: float = 0.15) -> Optional[np.ndarray]:
    """
    YOLO로 번호판 영역을 검출하여 타이트 크롭 반환.
    검출 실패 / 모델 로드 실패 시 None 반환 → 기존 OCR 파이프라인으로 폴백.

    Args:
        frame: BGR 이미지 (cv2 포맷)
        conf_threshold: YOLO 신뢰도 하한 (기본 0.15)

    Returns:
        번호판 크롭 이미지 (BGR) 또는 None
    """
    model = _get_plate_model()
    if model is None:
        return None

    try:
        results = model(frame, conf=conf_threshold, verbose=False)
        if not results or not results[0].boxes or len(results[0].boxes) == 0:
            logger.debug("[PlateDetector] 번호판 미검출")
            return None

        boxes = results[0].boxes

        # 한국 번호판 가로세로비(4.7:1)에 가장 가까운 박스 선택
        TARGET_RATIO = 4.7
        valid_indices = [i for i in range(len(boxes)) if float(boxes.conf[i]) >= 0.15]
        if valid_indices:
            best_idx = min(
                valid_indices,
                key=lambda i: abs(
                    (float(boxes.xyxy[i][2]) - float(boxes.xyxy[i][0])) /
                    max(float(boxes.xyxy[i][3]) - float(boxes.xyxy[i][1]), 1) - TARGET_RATIO
                )
            )
        else:
            best_idx = int(boxes.conf.argmax())

        x1, y1, x2, y2 = [int(v) for v in boxes.xyxy[best_idx].tolist()]

        pad = 8
        h, w = frame.shape[:2]
        x1 = max(0, x1 - pad)
        y1 = max(0, y1 - pad)
        x2 = min(w, x2 + pad)
        y2 = min(h, y2 + pad)

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 20:
            logger.debug("[PlateDetector] 크롭 크기 미달 — 폴백")
            return None

        conf = float(boxes.conf[best_idx])
        ratio = (x2 - x1) / max(y2 - y1, 1)
        logger.info("[PlateDetector] 번호판 검출: (%d,%d)-(%d,%d) conf=%.3f ratio=%.1f",
                    x1, y1, x2, y2, conf, ratio)
        return crop

    except Exception as e:
        logger.warning("[PlateDetector] 검출 예외: %s", e)
        return None
