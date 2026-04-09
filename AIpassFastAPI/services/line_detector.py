import time
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_line_crossing_history: dict = {}
# { track_id: {"side": int, "last_seen": float, "cooldown_until": float, "is_reported": bool} }


def _get_side(cx: float, cy: float, x1: int, y1: int, x2: int, y2: int) -> int:
    """점(cx,cy)이 선분의 어느 쪽인지 외적 부호로 판정. +1 또는 -1."""
    cross = (x2 - x1) * (cy - y1) - (y2 - y1) * (cx - x1)
    return 1 if cross >= 0 else -1


def garbage_collection_line(current_time: float) -> None:
    """5초 이상 미탐지 차량 히스토리 제거"""
    stale = [
        tid for tid, d in _line_crossing_history.items()
        if current_time - d.get("last_seen", 0) > 5.0
    ]
    for tid in stale:
        del _line_crossing_history[tid]


def process_line_crossing_detection(results) -> list:
    """실선 침범 감지 — process_headless_inference()와 동일한 반환 구조.

    반환: [{"track_id": int, "payload": dict}, ...]
    """
    from core.config import settings
    current_time = time.time()
    garbage_collection_line(current_time)

    x1, y1 = settings.LINE_X1, settings.LINE_Y1
    x2, y2 = settings.LINE_X2, settings.LINE_Y2
    events = []

    if not (results[0].boxes and results[0].boxes.id is not None):
        return events

    boxes = results[0].boxes.xywh.cpu().numpy()
    track_ids = results[0].boxes.id.int().cpu().tolist()

    for box, track_id in zip(boxes, track_ids):
        cx, cy, w, h = float(box[0]), float(box[1]), float(box[2]), float(box[3])
        # 타이어 접지면 (speed_detector와 동일 방식)
        foot_y = cy + h / 2.0

        current_side = _get_side(cx, foot_y, x1, y1, x2, y2)

        if track_id not in _line_crossing_history:
            _line_crossing_history[track_id] = {
                "side": current_side,
                "last_seen": current_time,
                "cooldown_until": 0.0,
                "is_reported": False,
            }
            continue

        state = _line_crossing_history[track_id]
        state["last_seen"] = current_time
        prev_side = state["side"]

        # 측면 변경 = 침범 발생
        if (current_side != prev_side
                and not state["is_reported"]
                and current_time > state["cooldown_until"]):
            state["is_reported"] = True
            state["cooldown_until"] = current_time + settings.LINE_CROSSING_COOLDOWN
            now = datetime.now(timezone.utc)
            payload = {
                "eventId": f"EVT-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
                "timestamp": now.isoformat(),
                "cameraLocation": settings.CAMERA_LOCATION_LINE,
                "violationType": "LINE_CROSSING",
                "speedKmh": 0.0,
            }
            logger.info(f"[LineCrossing] Track {track_id} crossed the line! Payload: {payload['eventId']}")
            events.append({"track_id": track_id, "payload": payload})

        # 쿨다운 이후 반대 방향으로 복귀 시 재단속 가능하도록 리셋
        if state["is_reported"] and current_time > state["cooldown_until"]:
            state["is_reported"] = False

        state["side"] = current_side

    return events
