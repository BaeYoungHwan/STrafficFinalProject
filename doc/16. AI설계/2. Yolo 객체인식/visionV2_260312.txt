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
from utils.http_client import http_client

logger = logging.getLogger(__name__)

def video_reader_worker(rtsp_url: str, meta_queue: Queue, lock: Lock, stop_event: Event):
    """[V2] SharedMemory 기반 OpenCV 워커 (Lock 동기화 보장)"""
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
            
            # [요구사항 3.2.1] 반드시 Lock을 획득한 상태에서 쓰기
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

class VisionEngine:
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.meta_queue = Queue(maxsize=3)
        self.latest_annotated_frame = None
        self.reader_process = None
        self.lock = Lock()
        self.stop_event = Event()
        
        # [V2] 이벤트 제어를 위한 현재 활성 트랙 ID 추적셋
        self.active_track_ids = set()
        
        logger.info(f"[Vision] Loading {settings.YOLO_MODEL}...")
        self.model = YOLO(settings.YOLO_MODEL)

    def start(self):
        self.stop_event.clear()
        self.reader_process = Process(
            target=video_reader_worker, 
            args=(self.rtsp_url, self.meta_queue, self.lock, self.stop_event), 
            daemon=True
        )
        self.reader_process.start()

# ... (상단 모듈 및 워커 프로세스 코드는 기존과 동일) ...

    async def process_inference_loop(self):
        """[V2] 비동기 추론 및 이벤트 기반 데이터 송출 루프 (긴급 차량 감지 수정본)"""
        try:
            meta = await asyncio.to_thread(self.meta_queue.get, True, 5.0)
        except queue.Empty:
            return
        except Exception as e:
            logger.error(f"Queue error: {e}")
            return

        def _read_shared_memory():
            existing_shm = shared_memory.SharedMemory(name=meta['shm_name'])
            try:
                with self.lock:
                    safe_frame = np.ndarray(meta['shape'], dtype=meta['dtype'], buffer=existing_shm.buf).copy()
                return safe_frame
            finally:
                existing_shm.close()

        try:
            frame = await asyncio.to_thread(_read_shared_memory)
        except FileNotFoundError:
            return

        # 🚨 [QA 수정 2.1] 일반 차량과 긴급 차량 클래스를 모두 합쳐서 모델에 전달
        all_target_classes = settings.TARGET_CLASSES + settings.EMERGENCY_CLASSES

        results = await asyncio.to_thread(
            self.model.track, 
            frame, 
            persist=True, 
            tracker="bytetrack.yaml", 
            verbose=False,
            imgsz=settings.INFERENCE_IMGSZ,
            conf=settings.CONF_THRESHOLD,
            classes=all_target_classes  # 🚨 수정된 필터링 파라미터 적용
        )
        
        annotated_frame = results[0].plot()
        
        if results[0].boxes and results[0].boxes.id is not None:
            id_list = results[0].boxes.id.int().cpu().tolist()
            current_frame_track_ids = set(id_list)
            
            for i, track_id in enumerate(id_list):
                if track_id not in self.active_track_ids:
                    box = results[0].boxes[i]
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id]
                    conf = float(box.conf[0])
                    x_center, y_center, width, height = box.xywh[0].tolist()
                    
                    # 🚨 [Flow C 로직] 감지된 차량이 긴급 차량일 경우 즉각 경보 발령
                    if class_id in settings.EMERGENCY_CLASSES:
                        emergency_payload = {
                            "event_id": f"emg_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}",
                            "event_type": "emergency_detected",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "camera_id": settings.CAMERA_ID,
                            "data": {
                                "track_id": f"track_{track_id}",
                                "class_name": class_name,
                                "confidence": round(conf, 3),
                                "action_required": "signal_override"
                            }
                        }
                        logger.critical(f"🚨 [EMERGENCY] {class_name} detected! Requesting immediate signal override.")
                        asyncio.create_task(http_client.send_payload("/api/v1/emergencies", emergency_payload))
                        
                        # 🚨 [QA 수정 3.1] 긴급 이벤트를 쐈다면 일반 이벤트로는 전송하지 않고 다음 객체로 넘어감
                        continue 

                    # --------------------------------------------------
                    # (일반 차량 진입 이벤트 로직)
                    # --------------------------------------------------
                    payload = {
                        "event_id": f"evt_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:4]}",
                        "event_type": "object_entered",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "camera_id": settings.CAMERA_ID,
                        "data": {
                            "track_id": f"track_{track_id}",
                            "class_name": class_name,
                            "confidence": round(conf, 3),
                            "bbox": {
                                "x_center": round(x_center, 1),
                                "y_center": round(y_center, 1),
                                "width": round(width, 1),
                                "height": round(height, 1)
                            }
                        }
                    }
                    
                    logger.info(f"[Vision Event] New object detected: {class_name} (Track: {track_id})")
                    asyncio.create_task(http_client.send_payload("/api/v1/vision/events", payload))
            
            self.active_track_ids = current_frame_track_ids
        else:
            self.active_track_ids.clear()

        resized_frame = await asyncio.to_thread(
            cv2.resize, annotated_frame, (settings.STREAM_MAX_WIDTH, settings.STREAM_MAX_HEIGHT)
        )
        self.latest_annotated_frame = resized_frame

# ... (VisionEngine stop 메서드 및 인스턴스 생성 유지) ...

def stop(self):
        if self.reader_process and self.reader_process.is_alive():
            self.stop_event.set() 
            self.reader_process.join(timeout=5) 
            if self.reader_process.is_alive():
                self.reader_process.terminate() 

vision_engine = VisionEngine(rtsp_url="rtsp://localhost:8554/mystream")