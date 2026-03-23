import cv2
import time
import logging
import os
import random
import glob as _glob
import numpy as np
import queue
import asyncio
from multiprocessing import Process, Queue, shared_memory, Lock, Event
from ultralytics import YOLO
from core.config import settings
from services.webhook_client import webhook_client
from services.ocr_storage import run_ocr_on_file
from utils.http_client import http_client

logger = logging.getLogger(__name__)

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

    _infer_counter = 0
    _last_results = None

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

        # 2프레임에 1회만 YOLO 추론 — 나머지는 이전 결과 재사용으로 CPU 부하 절반 감소
        _infer_counter += 1
        if _infer_counter % 2 == 0 and _last_results is not None:
            results = _last_results
        else:
            results = model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False,
                                  imgsz=settings.INFERENCE_IMGSZ, conf=settings.CONF_THRESHOLD,
                                  classes=settings.TARGET_CLASSES)
            _last_results = results

        # [과속 감지] process_headless_inference 호출 → 과속 이벤트 목록 반환
        speeding_events = process_headless_inference(results)

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
        payload["imageUrl"] = result["image_url"]   # "numberplate/filename.jpg" (프론트에서 prefix 추가)
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
        self.mjpeg_queue = Queue(maxsize=10)

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
        while not self.stop_event.is_set():
            try:
                event = await asyncio.to_thread(self.event_queue.get, True, 0.1)

                if event["type"] == "SPEEDING_VIOLATION":
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
