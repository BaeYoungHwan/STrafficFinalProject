import time
import uuid
import cv2
import logging
import numpy as np
from datetime import datetime, timezone
from collections import deque
from core.config import settings as _cfg

logger = logging.getLogger(__name__)

vehicle_history = {}
SPEED_LIMIT_KMH = _cfg.SPEED_LIMIT_KMH
MAX_PLAUSIBLE_SPEED_KMH = _cfg.MAX_PLAUSIBLE_SPEED_KMH
EMA_ALPHA = _cfg.EMA_ALPHA
CONSECUTIVE_OVER_THRESHOLD = _cfg.CONSECUTIVE_OVER_THRESHOLD

# 강화대교 카메라 전용 호모그래피 (640x480 실제 화면 분석 기반)
# src_pts: 영상 내 도로 4개 꼭짓점 (픽셀)
# dst_pts: 실제 도로 좌표 (미터) — 강화대교 4차선 폭 약 16m, 구간 실측 55m
src_pts = np.array([[285, 460], [615, 460], [560, 300], [445, 300]], dtype=np.float32)
dst_pts = np.array([[0, 0], [20, 0], [20, 55], [0, 55]], dtype=np.float32)
HOMOGRAPHY_MATRIX = cv2.getPerspectiveTransform(src_pts, dst_pts)

# 역방향(서울↑) 전용 호모그래피 — y=180-300 영역으로 확장 (120px → 약 40m 구간)
# 하행과 동일한 m/px 비율(~0.34m/px) 적용, 실측 후 보정 권장
src_pts_rev = np.array([[350, 180], [540, 180], [560, 300], [285, 300]], dtype=np.float32)
dst_pts_rev = np.array([[0, 0], [16, 0], [16, 40], [0, 40]], dtype=np.float32)
HOMOGRAPHY_MATRIX_REVERSE = cv2.getPerspectiveTransform(src_pts_rev, dst_pts_rev)

def get_real_world_distance(pt1, pt2):
    # 평균 y 위치 기준으로 정방향/역방향 호모그래피 자동 선택
    avg_y = (pt1[1] + pt2[1]) / 2
    matrix = HOMOGRAPHY_MATRIX_REVERSE if avg_y < 300 else HOMOGRAPHY_MATRIX
    pts = np.array([[pt1], [pt2]], dtype=np.float32)
    transformed_pts = cv2.perspectiveTransform(pts, matrix)
    return np.linalg.norm(transformed_pts[0][0] - transformed_pts[1][0])

def update_and_get_speed(track_id: int, center_x: float, y_max: float, current_time: float) -> float:
    """[V3.2] 타이어 접지면(y_max) 기반 호모그래피 + EMA 속도 연산 (상한선 클리핑 버그 수정)"""
    if track_id not in vehicle_history:
        vehicle_history[track_id] = {
            'history': deque(maxlen=15),
            'last_seen': current_time,
            'ema_speed': 0.0,
            'is_reported': False,
            'consecutive_over': 0,
            'last_reported_time': 0.0,
        }

    history = vehicle_history[track_id]['history']
    history.append((current_time, (center_x, y_max)))
    vehicle_history[track_id]['last_seen'] = current_time

    if len(history) < 5: return 0.0

    prev_time, prev_pt = history[-2]
    latest_time, latest_pt = history[-1]

    time_diff = latest_time - prev_time
    if time_diff <= 0: return 0.0

    distance_m = get_real_world_distance(prev_pt, latest_pt)
    raw_speed_kmh = (distance_m / time_diff) * 3.6

    # [Fix] 상한선을 raw 기준으로 먼저 검사 — 스케일 팩터로 인한 초과 방지
    max_raw = MAX_PLAUSIBLE_SPEED_KMH / max(_cfg.SPEED_SCALE_FACTOR, 1e-6)
    if raw_speed_kmh > max_raw:
        prev_scaled = vehicle_history[track_id]['ema_speed'] * _cfg.SPEED_SCALE_FACTOR
        return round(float(min(prev_scaled, MAX_PLAUSIBLE_SPEED_KMH)), 1)

    prev_ema = vehicle_history[track_id]['ema_speed']
    smoothed_speed = raw_speed_kmh if prev_ema == 0.0 else (EMA_ALPHA * raw_speed_kmh) + ((1 - EMA_ALPHA) * prev_ema)
    # EMA 저장값 자체도 상한선으로 클리핑 — 누적 오버슈트 방지
    vehicle_history[track_id]['ema_speed'] = min(smoothed_speed, max_raw)

    return round(float(min(smoothed_speed * _cfg.SPEED_SCALE_FACTOR, MAX_PLAUSIBLE_SPEED_KMH)), 1)

def garbage_collection(current_time: float):
    stale_ids = [t_id for t_id, data in vehicle_history.items() if current_time - data['last_seen'] > 2.0]
    for t_id in stale_ids:
        del vehicle_history[t_id]

def process_headless_inference(results) -> list:
    """[Process B] 과속 감지 워커.

    반환: [{"track_id": int, "speed": float, "payload": dict}, ...]
    과속 감지된 차량 목록을 반환. vision.py에서 이미지 선정 후 큐에 적재.
    """
    current_time = time.time()
    garbage_collection(current_time)

    speeding_events = []

    if results[0].boxes and results[0].boxes.id is not None:
        boxes = results[0].boxes.xywh.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()

        for box, track_id in zip(boxes, track_ids):
            x_center, y_center, _, height = box
            y_max = y_center + (height / 2)

            current_speed = update_and_get_speed(track_id, x_center, y_max, current_time)

            data = vehicle_history[track_id]

            if current_speed > SPEED_LIMIT_KMH:
                data['consecutive_over'] += 1
            else:
                data['consecutive_over'] = 0
                data['is_reported'] = False

            elapsed = current_time - data['last_reported_time']
            if (current_speed > SPEED_LIMIT_KMH
                    and data['consecutive_over'] >= CONSECUTIVE_OVER_THRESHOLD
                    and not data['is_reported']
                    and elapsed >= _cfg.SPEEDING_COOLDOWN):
                data['is_reported'] = True
                data['last_reported_time'] = current_time

                payload = {
                    "eventId": f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cameraLocation": "강화대교_메인_01",
                    "violationType": "SPEEDING",
                    "speedKmh": current_speed,
                }
                speeding_events.append({
                    "track_id": track_id,
                    "speed": current_speed,
                    "payload": payload,
                })

    return speeding_events
