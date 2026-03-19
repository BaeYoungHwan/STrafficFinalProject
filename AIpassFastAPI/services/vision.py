import cv2
import time
import uuid
import logging
import numpy as np
import queue
import asyncio
from datetime import datetime, timezone
from multiprocessing import Process, Queue, shared_memory, Lock, Event
from ultralytics import YOLO
from core.config import settings
from services.webhook_client import webhook_client
from services.ocr_storage import process_violation_task
from utils.http_client import http_client

logger = logging.getLogger(__name__)

INTERSECTION_ROI = np.array([[200, 300], [1000, 300], [1200, 700], [50, 700]], np.int32)
VIOLATION_LINE_Y = 600

def video_reader_worker(rtsp_url: str, meta_queue: Queue, lock: Lock, stop_event: Event):
    """[Process A] 영상 수집 워커 (SharedMemory 사용)"""
    cap = None
    shm = None
    try:
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            logger.error(f"[Vision] Failed to open stream: {rtsp_url}")
            return

        ret, frame = cap.read()
        if not ret: return
            
        shm_size = frame.nbytes
        shm = shared_memory.SharedMemory(create=True, size=shm_size)
        shm_name = shm.name
        
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                if cap: cap.release() 
                time.sleep(2)
                cap = cv2.VideoCapture(rtsp_url)
                continue
            
            if frame.nbytes != shm_size:
                logger.error("[Vision] Resolution changed! Exiting worker.")
                break 
                
            shared_array = np.ndarray(frame.shape, dtype=frame.dtype, buffer=shm.buf)
            
            with lock:
                np.copyto(shared_array, frame)
            
            meta = {'shm_name': shm_name, 'shape': frame.shape, 'dtype': frame.dtype}
            try:
                meta_queue.put_nowait(meta)
            except queue.Full:
                try:
                    meta_queue.get_nowait()
                    meta_queue.put_nowait(meta)
                except queue.Empty:
                    pass
                    
    except Exception as e:
        logger.error(f"[Vision] Worker error: {e}")
    finally:
        if cap: cap.release()
        if shm: 
            shm.close()
            shm.unlink()

def ai_inference_worker(meta_queue: Queue, event_queue: Queue, mjpeg_queue: Queue, lock: Lock, stop_event: Event):
    """[Process B] 무거운 AI 연산 및 시각화 렌더링 워커"""
    logger.info(f"[AI Engine] Process started. Loading {settings.YOLO_MODEL}...")
    model = YOLO(settings.YOLO_MODEL)
    active_tracks = set()

    from services.speed_detector import (
        process_headless_inference,
        vehicle_history,
        SPEED_LIMIT_KMH,
    )
    
    def safe_put(event_data):
        try:
            event_queue.put_nowait(event_data)
        except queue.Full:
            pass # 이벤트 드랍 (FPS 유지)

    while not stop_event.is_set():
        try:
            meta = meta_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        existing_shm = shared_memory.SharedMemory(name=meta['shm_name'])
        try:
            with lock:
                frame = np.ndarray(meta['shape'], dtype=meta['dtype'], buffer=existing_shm.buf).copy()
        finally:
            existing_shm.close()

        all_classes = settings.TARGET_CLASSES + settings.EMERGENCY_CLASSES
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False,
                              imgsz=settings.INFERENCE_IMGSZ, conf=settings.CONF_THRESHOLD, classes=all_classes)

        if results[0].boxes and results[0].boxes.id is not None:
            id_list = results[0].boxes.id.int().cpu().tolist()
            current_tracks = set(id_list)

            for i, track_id in enumerate(id_list):
                box = results[0].boxes[i]
                class_id = int(box.cls[0])
                class_name = model.names[class_id]
                conf = float(box.conf[0])
                x_center, y_center, width, height = box.xywh[0].tolist()

                # Flow C (긴급 차량)
                if class_id in settings.EMERGENCY_CLASSES and track_id not in active_tracks:
                    safe_put({"type": "EMERGENCY", "track_id": track_id, "class": class_name, "conf": conf})
                    continue

                # Flow A (혼잡도 진입)
                is_inside_roi = cv2.pointPolygonTest(INTERSECTION_ROI, (x_center, y_center), False) >= 0
                if is_inside_roi and track_id not in active_tracks:
                    safe_put({"type": "ENTER_ROI", "track_id": track_id})

                # Flow B (단속선 통과 및 크롭)
                if y_center > VIOLATION_LINE_Y and track_id not in active_tracks:
                    x1 = max(0, int(x_center - width/2))
                    y1 = max(0, int(y_center))
                    x2 = min(frame.shape[1], int(x_center + width/2))
                    y2 = min(frame.shape[0], int(y_center + height/2))

                    plate_crop = frame[y1:y2, x1:x2]
                    if plate_crop.size > 0:
                        safe_put({
                            "type": "VIOLATION",
                            "track_id": track_id,
                            "crop": plate_crop,
                            "violation_type": "line_crossing",
                            "confidence": conf
                        })

            exited_tracks = active_tracks - current_tracks
            for t_id in exited_tracks:
                safe_put({"type": "EXIT_ROI", "track_id": t_id})
            active_tracks = current_tracks
        else:
            for t_id in active_tracks:
                safe_put({"type": "EXIT_ROI", "track_id": t_id})
            active_tracks.clear()

        # [과속 감지] Process B에서 speed_detector 호출
        process_headless_inference(results, event_queue)

        # [Web Demo] 3단계 경량화 시각화 렌더링
        annotated_frame = results[0].plot()
        resized_frame = cv2.resize(annotated_frame, (640, 480))

        # [과속 오버레이] 각 차량 bbox 위에 속도 텍스트 표시
        if results[0].boxes and results[0].boxes.id is not None:
            id_list = results[0].boxes.id.int().cpu().tolist()
            scale_x = 640 / frame.shape[1]
            scale_y = 480 / frame.shape[0]
            for i, track_id in enumerate(id_list):
                data = vehicle_history.get(track_id)
                if data is None:
                    continue
                speed = data.get("ema_speed", 0.0)
                if speed <= 0:
                    continue
                box = results[0].boxes[i]
                x_center, y_center, width, _ = box.xywh[0].tolist()
                x_px = int((x_center - width / 2) * scale_x)
                y_px = max(0, int(y_center * scale_y) - 10)
                color = (0, 0, 255) if speed > SPEED_LIMIT_KMH else (0, 220, 0)
                label = f"{speed:.0f} km/h"
                cv2.putText(resized_frame, label, (x_px, y_px),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

        cv2.line(resized_frame, (0, int(VIOLATION_LINE_Y * 480/frame.shape[0])),
                 (640, int(VIOLATION_LINE_Y * 480/frame.shape[0])), (0, 0, 255), 2)
        
        ret, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        if ret:
            frame_bytes = buffer.tobytes()
            try:
                mjpeg_queue.put_nowait(frame_bytes)
            except queue.Full:
                # 🚨 [수정] 큐가 꽉 차면 낡은 프레임을 즉시 빼버리고 최신 프레임을 주입!
                try:
                    mjpeg_queue.get_nowait() 
                    mjpeg_queue.put_nowait(frame_bytes) 
                except:
                    pass

class VisionEngine:
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.meta_queue = Queue(maxsize=3)
        self.event_queue = Queue(maxsize=100)
        self.mjpeg_queue = Queue(maxsize=2) 
        
        self.reader_process = None
        self.ai_process = None
        self.lock = Lock()
        self.stop_event = Event()

    def start(self):
        self.stop_event.clear()
        self.reader_process = Process(target=video_reader_worker, args=(self.rtsp_url, self.meta_queue, self.lock, self.stop_event))
        self.ai_process = Process(target=ai_inference_worker, args=(self.meta_queue, self.event_queue, self.mjpeg_queue, self.lock, self.stop_event))
        
        self.reader_process.start()
        self.ai_process.start()

    async def process_event_loop(self):
        """[Process C] 가벼운 API 통신 및 이벤트 처리 루프"""
        from services.aggregator import congestion_engine 
        # 🚨 [신규 추가] Webhook 클라이언트 임포트
        from services.webhook_client import webhook_client
        
        while not self.stop_event.is_set():
            try:
                event = await asyncio.to_thread(self.event_queue.get, True, 0.1)
                
                if event["type"] == "EMERGENCY":
                    payload = {
                        "event_id": f"emg_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}",
                        "event_type": "emergency_detected",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "camera_id": settings.CAMERA_ID,
                        "data": {
                            "track_id": f"track_{event['track_id']}",
                            "class_name": event["class"],
                            "confidence": round(event.get("conf", 0.99), 3),
                            "action_required": "signal_override"
                        }
                    }
                    asyncio.create_task(http_client.send_payload("/api/v1/emergencies", payload))
                    
                elif event["type"] == "ENTER_ROI":
                    await congestion_engine.record_entry(event["track_id"])
                    
                elif event["type"] == "EXIT_ROI":
                    await congestion_engine.record_exit(event["track_id"])
                    
                # 🚨 [V3.1 개편] Headless AI의 Mock LPR JSON 웹훅 전송 로직 추가
                elif event["type"] == "WEBHOOK_VIOLATION":
                    payload = event["payload"]
                    # Process B가 만들어준 완제품 JSON을 비동기로 쏘기만 합니다.
                    asyncio.create_task(webhook_client.send_violation(payload))
                    
                # 🗑️ [삭제/주석] 기존 무거운 이미지 크롭 및 OCR 처리 로직은 폐기 (Headless 전환)
                # elif event["type"] == "VIOLATION":
                #     asyncio.create_task(process_violation_task(
                #         event["crop"], event["violation_type"], event["confidence"]
                #     ))
                    
            except queue.Empty:
                await asyncio.sleep(0.01)

    def stop(self):
        self.stop_event.set()
        if self.reader_process: self.reader_process.join(3)
        if self.ai_process: self.ai_process.join(3)

    def restart(self, new_url: str):
        """동영상 소스 URL을 변경하고 프로세스를 재시작한다."""
        logger.info(f"[Vision] Restarting engine with new source: {new_url}")
        self.stop()
        self.rtsp_url = new_url
        # 큐 초기화
        while not self.meta_queue.empty():
            try: self.meta_queue.get_nowait()
            except: break
        while not self.mjpeg_queue.empty():
            try: self.mjpeg_queue.get_nowait()
            except: break
        self.start()

# 글로벌 인스턴스 — VIDEO_SOURCE_URL은 .env 또는 config 기본값에서 읽음
vision_engine = VisionEngine(rtsp_url=settings.VIDEO_SOURCE_URL)