import time
import uuid
import cv2
import logging
import numpy as np
from datetime import datetime, timezone
from collections import deque
import queue
from core.config import settings as _cfg

logger = logging.getLogger(__name__)

vehicle_history = {} 
SPEED_LIMIT_KMH = 50.0 
EMA_ALPHA = 0.3  # 지수이동평균 가중치

# 가상의 강화대교 호모그래피 매트릭스
src_pts = np.array([[500, 300], [780, 300], [1280, 720], [0, 720]], dtype=np.float32)
dst_pts = np.array([[0, 0], [10, 0], [10, 30], [0, 30]], dtype=np.float32)
HOMOGRAPHY_MATRIX = cv2.getPerspectiveTransform(src_pts, dst_pts)

def get_real_world_distance(pt1, pt2):
    pts = np.array([[pt1], [pt2]], dtype=np.float32)
    transformed_pts = cv2.perspectiveTransform(pts, HOMOGRAPHY_MATRIX)
    return np.linalg.norm(transformed_pts[0][0] - transformed_pts[1][0])

def update_and_get_speed(track_id: int, center_x: float, y_max: float, current_time: float) -> float:
    """[V3.1] 타이어 접지면(y_max) 기반 호모그래피 + EMA 속도 연산"""
    if track_id not in vehicle_history:
        vehicle_history[track_id] = {
            'history': deque(maxlen=15), 
            'last_seen': current_time, 
            'ema_speed': 0.0,
            'is_reported': False # 멱등성 보장 플래그
        }
        
    history = vehicle_history[track_id]['history']
    history.append((current_time, (center_x, y_max)))
    vehicle_history[track_id]['last_seen'] = current_time
    
    if len(history) < 5: return 0.0  # Warm-up: EMA 수렴 전 초기 노이즈 억제

    prev_time, prev_pt = history[-2]
    latest_time, latest_pt = history[-1]

    time_diff = latest_time - prev_time
    if time_diff <= 0: return 0.0

    distance_m = get_real_world_distance(prev_pt, latest_pt)
    raw_speed_kmh = (distance_m / time_diff) * 3.6
    
    prev_ema = vehicle_history[track_id]['ema_speed']
    smoothed_speed = raw_speed_kmh if prev_ema == 0.0 else (EMA_ALPHA * raw_speed_kmh) + ((1 - EMA_ALPHA) * prev_ema)
        
    vehicle_history[track_id]['ema_speed'] = smoothed_speed  # raw 저장 (scale 미적용)
    return round(smoothed_speed * _cfg.SPEED_SCALE_FACTOR, 1)

def garbage_collection(current_time: float):
    stale_ids = [t_id for t_id, data in vehicle_history.items() if current_time - data['last_seen'] > 2.0]
    for t_id in stale_ids:
        del vehicle_history[t_id]

def process_headless_inference(results, event_queue):
    """[Process B] 무거운 AI 추론 워커 (통신 수행 안 함)"""
    current_time = time.time()
    garbage_collection(current_time)
    
    if results[0].boxes and results[0].boxes.id is not None:
        boxes = results[0].boxes.xywh.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        
        for box, track_id in zip(boxes, track_ids):
            x_center, y_center, _, height = box
            
            # 🚨 [QA 2.1 반영] 중심이 아닌 '타이어가 닿는 하단 중앙점'으로 기준 변경
            y_max = y_center + (height / 2)
            
            current_speed = update_and_get_speed(track_id, x_center, y_max, current_time)
            
            if current_speed > SPEED_LIMIT_KMH and not vehicle_history[track_id]['is_reported']:
                vehicle_history[track_id]['is_reported'] = True
                
                payload = {
                    "eventId": f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "cameraLocation": "강화대교_메인_01",
                    "violationType": "SPEEDING",
                    "speedKmh": current_speed,
                    "mockLprData": {
                        "plateNumber": "123가4567",
                        "confidence": 0.98,
                        "plateImageBase64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" # 더미 투명 픽셀
                    }
                }
                
                # 🚨 [QA 2.2 반영] 직접 통신하지 않고 IPC 큐에 안전하게 적재
                try:
                    event_queue.put_nowait({"type": "WEBHOOK_VIOLATION", "payload": payload})
                except queue.Full:
                    pass