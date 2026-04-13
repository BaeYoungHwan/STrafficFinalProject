import time
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_line_crossing_history: dict = {}
# { track_id: {"side1": int, "side2": int, "last_seen": float, "cooldown_until": float, "is_reported": bool} }

# GC 쓰로틀: 매 프레임(25fps) 대신 1초마다만 실행
_last_gc_time: float = 0.0
_GC_INTERVAL: float = 1.0

# _zone_top 사전계산 (settings 상수 — 매 프레임 재계산 불필요)
from core.config import settings as _lc_settings
_ZONE_TOP: float = min(
    _lc_settings.LINE_Y1,
    _lc_settings.LINE_Y2,
    _lc_settings.LINE2_Y1,
    _lc_settings.LINE2_Y2,
)


def _get_side(cx: float, cy: float, x1: int, y1: int, x2: int, y2: int) -> int:
    """점(cx,cy)이 선분의 어느 쪽인지 외적 부호로 판정. +1 또는 -1."""
    cross = (x2 - x1) * (cy - y1) - (y2 - y1) * (cx - x1)
    return 1 if cross >= 0 else -1


def get_violating_ids() -> set:
    """현재 쿨다운 중인 (실선 침범 감지된) track_id 집합 반환"""
    now = time.time()
    return {
        tid for tid, d in _line_crossing_history.items()
        if d.get("is_reported") and now < d.get("cooldown_until", 0)
    }


def garbage_collection_line(current_time: float) -> None:
    """5초 이상 미탐지 차량 히스토리 제거"""
    stale = [
        tid for tid, d in _line_crossing_history.items()
        if current_time - d.get("last_seen", 0) > 5.0
    ]
    for tid in stale:
        del _line_crossing_history[tid]


def process_line_crossing_detection(results) -> list:
    """실선 침범 감지 (하행선 + 상행선 2선 동시 감지).

    반환: [{"track_id": int, "payload": dict}, ...]
    """
    global _last_gc_time
    from core.config import settings
    current_time = time.time()
    # GC 쓰로틀: 1초마다만 실행 (25fps → 초당 1회로 감소)
    if current_time - _last_gc_time >= _GC_INTERVAL:
        garbage_collection_line(current_time)
        _last_gc_time = current_time

    # 하행선 실선 좌표
    x1, y1 = settings.LINE_X1, settings.LINE_Y1
    x2, y2 = settings.LINE_X2, settings.LINE_Y2
    # 상행선 실선 좌표
    x1b, y1b = settings.LINE2_X1, settings.LINE2_Y1
    x2b, y2b = settings.LINE2_X2, settings.LINE2_Y2

    events = []

    if not (results[0].boxes and results[0].boxes.id is not None):
        return events

    boxes = results[0].boxes.xywh.cpu().numpy()
    track_ids = results[0].boxes.id.int().cpu().tolist()

    for box, track_id in zip(boxes, track_ids):
        cx, cy, w, h = float(box[0]), float(box[1]), float(box[2]), float(box[3])
        foot_y = cy + h / 2.0

        # 탐지 구간 위에 있는 차량은 완전 무시
        if foot_y < _ZONE_TOP:
            continue

        # 선분 Y 범위 내에서만 침범 판정
        in_zone1 = min(y1, y2) <= foot_y <= max(y1, y2)
        in_zone2 = min(y1b, y2b) <= foot_y <= max(y1b, y2b)

        side1 = _get_side(cx, foot_y, x1, y1, x2, y2)
        side2 = _get_side(cx, foot_y, x1b, y1b, x2b, y2b)

        if track_id not in _line_crossing_history:
            _line_crossing_history[track_id] = {
                "side1": side1,
                "side2": side2,
                "pending_cross1": 0,  # 연속 side 변화 카운터 (하행선)
                "pending_cross2": 0,  # 연속 side 변화 카운터 (상행선)
                "last_seen": current_time,
                "cooldown_until": 0.0,
                "is_reported": False,
            }
            continue

        state = _line_crossing_history[track_id]
        state["last_seen"] = current_time
        prev_side1 = state["side1"]
        prev_side2 = state["side2"]

        # 연속 2프레임 side 변화 시에만 침범으로 판정 (노이즈 오탐 방지)
        if in_zone1 and side1 != prev_side1:
            state["pending_cross1"] += 1
        else:
            state["pending_cross1"] = 0

        if in_zone2 and side2 != prev_side2:
            state["pending_cross2"] += 1
        else:
            state["pending_cross2"] = 0

        crossed = (
            state["pending_cross1"] >= 3 or
            state["pending_cross2"] >= 3
        )

        if (crossed
                and not state["is_reported"]
                and current_time > state["cooldown_until"]):
            state["is_reported"] = True
            state["cooldown_until"] = current_time + settings.LINE_CROSSING_COOLDOWN
            state["pending_cross1"] = 0
            state["pending_cross2"] = 0
            # 침범 확정 후 side 기준 갱신
            state["side1"] = side1
            state["side2"] = side2
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
        elif not crossed:
            # 침범 아닌 경우에만 side 기준 갱신 (pending 중엔 기준 유지)
            if state["pending_cross1"] == 0:
                state["side1"] = side1
            if state["pending_cross2"] == 0:
                state["side2"] = side2

        # 쿨다운 이후 반대 방향으로 복귀 시 재단속 가능하도록 리셋
        if state["is_reported"] and current_time > state["cooldown_until"]:
            state["is_reported"] = False

    return events
