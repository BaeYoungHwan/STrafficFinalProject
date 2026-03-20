import cv2
import time
import uuid
import logging
import os
import random
import glob as _glob
import numpy as np
import queue
import asyncio
from datetime import datetime, timezone
from multiprocessing import Process, Queue, shared_memory, Lock, Event
from ultralytics import YOLO
from core.config import settings
from services.webhook_client import webhook_client
from services.ocr_storage import process_violation_task, run_ocr_on_file
from utils.http_client import http_client

logger = logging.getLogger(__name__)

# 강화대교 카메라 전용 좌표 (640x480 기준, 실제 화면 분석으로 보정)
INTERSECTION_ROI = np.array([[285, 480], [615, 480], [560, 230], [445, 230]], np.int32)
VIOLATION_LINE_Y = 360          # 정방향(강화↓) 단속선 — y 증가 방향
VIOLATION_LINE_Y_REVERSE = 240  # 역방향(서울↑) 단속선 — y 감소 방향

# carnumber 이미지 목록 캐시 (Process B에서 1회 로드)
_CARNUMBER_IMAGES: list = []

def _get_carnumber_images() -> list:
    global _CARNUMBER_IMAGES
    if not _CARNUMBER_IMAGES:
        _CARNUMBER_IMAGES = (
            _glob.glob("data/carnumber/*.jpeg") +
            _glob.glob("data/carnumber/*.jpg")
        )
        logger.info(f"[VisionEngine] carnumber 이미지 {len(_CARNUMBER_IMAGES)}개 로드됨.")
    return _CARNUMBER_IMAGES


def video_reader_worker(rtsp_url: str, meta_queue: Queue, lock: Lock, stop_event: Event):
    """[Process A] 영상 수집 워커 (SharedMemory 사용)"""
    from core.config import settings as _settings
    _frame_interval = 1.0 / _settings.STREAM_FPS_LIMIT

    cap = None
    shm = None
    try:
        while not stop_event.is_set():
            cap = cv2.VideoCapture(rtsp_url)
            if cap.isOpened():
                break
            logger.warning(f"[Vision] Cannot open stream, retrying in 3s: {rtsp_url}")
            time.sleep(3)
        else:
            return

        ret, frame = cap.read()
        if not ret: return

        shm_size = frame.nbytes
        shm = shared_memory.SharedMemory(create=True, size=shm_size)
        shm_name = shm.name

        while not stop_event.is_set():
            _t0 = time.time()

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

            elapsed = time.time() - _t0
            if elapsed < _frame_interval:
                time.sleep(_frame_interval - elapsed)

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
        MAX_PLAUSIBLE_SPEED_KMH,
    )

    def safe_put(event_data):
        try:
            event_queue.put_nowait(event_data)
        except queue.Full:
            pass

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

                # Flow B (단속선 통과 — 정방향/역방향 모두 감지)
                # 정방향(강화↓): y_center > VIOLATION_LINE_Y (y 증가, 카메라 쪽으로 접근)
                # 역방향(서울↑): y_center < VIOLATION_LINE_Y_REVERSE (y 감소, 카메라에서 멀어짐)
                is_forward  = y_center > VIOLATION_LINE_Y
                is_reverse  = y_center < VIOLATION_LINE_Y_REVERSE

                if (is_forward or is_reverse) and track_id not in active_tracks:
                    if is_forward:
                        # 정방향 — 전면 번호판: 차량 하단 1/4
                        px1 = max(0, int(x_center - width * 0.35))
                        py1 = max(0, int(y_center + height * 0.15))
                        px2 = min(frame.shape[1], int(x_center + width * 0.35))
                        py2 = min(frame.shape[0], int(y_center + height * 0.5))
                    else:
                        # 역방향 — 후면 번호판: 차량 상단 1/4
                        px1 = max(0, int(x_center - width * 0.35))
                        py1 = max(0, int(y_center - height * 0.5))
                        px2 = min(frame.shape[1], int(x_center + width * 0.35))
                        py2 = min(frame.shape[0], int(y_center - height * 0.15))

                    plate_crop = frame[py1:py2, px1:px2]
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

        # [과속 감지] process_headless_inference 호출 → 과속 이벤트 목록 반환
        speeding_events = process_headless_inference(results, event_queue)

        # 과속 감지된 차량에 대해 carnumber 랜덤 이미지 선정 후 이벤트 큐에 적재
        carnumber_images = _get_carnumber_images()
        for evt in speeding_events:
            if not carnumber_images:
                logger.warning("[VisionEngine] carnumber 이미지 없음. 과속 이벤트 스킵.")
                continue
            src_path = random.choice(carnumber_images)
            evt["payload"]["src_image_path"] = src_path
            safe_put({"type": "SPEEDING_VIOLATION", "payload": evt["payload"]})

        # [Web Demo] 시각화 렌더링
        annotated_frame = results[0].plot(labels=False)
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
                raw_speed = data.get("ema_speed", 0.0)
                speed = min(raw_speed * settings.SPEED_SCALE_FACTOR, MAX_PLAUSIBLE_SPEED_KMH)
                if speed <= 0:
                    continue
                box = results[0].boxes[i]
                x_center, y_center, width, _ = box.xywh[0].tolist()
                x_px = int((x_center - width / 2) * scale_x)
                y_px = max(0, int(y_center * scale_y) - 10)
                if speed >= 70:
                    color = (0, 0, 255)
                elif speed >= 60:
                    color = (0, 220, 0)
                elif speed >= 50:
                    color = (255, 255, 255)
                else:
                    continue
                label = f"ID:{track_id} {speed:.0f}km/h"
                cv2.putText(resized_frame, label, (x_px, y_px),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

        # 정방향 단속선 (빨간색) + 역방향 단속선 (파란색)
        fwd_y = int(VIOLATION_LINE_Y * 480 / frame.shape[0])
        rev_y = int(VIOLATION_LINE_Y_REVERSE * 480 / frame.shape[0])
        cv2.line(resized_frame, (0, fwd_y), (640, fwd_y), (0, 0, 255), 2)
        cv2.line(resized_frame, (0, rev_y), (640, rev_y), (255, 100, 0), 2)

        ret, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        if ret:
            frame_bytes = buffer.tobytes()
            try:
                mjpeg_queue.put_nowait(frame_bytes)
            except queue.Full:
                try:
                    mjpeg_queue.get_nowait()
                    mjpeg_queue.put_nowait(frame_bytes)
                except:
                    pass


async def _handle_speeding_violation(payload: dict):
    """과속 이벤트: carnumber 이미지에 OCR 실행 → webhook 전송"""
    src_path = payload.pop("src_image_path", None)

    if src_path and os.path.exists(src_path):
        result = await run_ocr_on_file(src_path)
        payload["plateNumber"] = result["plate_number"]
        payload["imageUrl"] = result["image_url"]
        payload["isCorrected"] = result.get("is_corrected", False)
        logger.info(f"[Speeding] OCR 완료 — 번호판: {result['plate_number']} | 이미지: {result['image_url']} | 수동검토: {result.get('is_corrected', False)}")
    else:
        payload["plateNumber"] = "미인식"
        payload["imageUrl"] = None
        logger.warning(f"[Speeding] carnumber 이미지 없음 — 미인식 처리")

    await webhook_client.send_violation(payload)


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

                elif event["type"] == "SPEEDING_VIOLATION":
                    # carnumber 랜덤 이미지 → OCR → webhook 전송
                    asyncio.create_task(_handle_speeding_violation(event["payload"]))

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
        while not self.meta_queue.empty():
            try: self.meta_queue.get_nowait()
            except: break
        while not self.mjpeg_queue.empty():
            try: self.mjpeg_queue.get_nowait()
            except: break
        self.start()


# 글로벌 인스턴스
vision_engine = VisionEngine(rtsp_url=settings.VIDEO_SOURCE_URL)
