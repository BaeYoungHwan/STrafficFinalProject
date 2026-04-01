import cv2
import time
import logging
import os
import random
import glob as _glob
import numpy as np
import queue
import asyncio
import threading
from multiprocessing import Process, Queue, shared_memory, Lock, Event
from ultralytics import YOLO
from core.config import settings
from services.webhook_client import webhook_client
from utils.http_client import http_client

logger = logging.getLogger(__name__)

# 과속 위반 처리 큐 — process_event_loop에서 put, _violation_worker에서 1개씩 소비
_violation_queue: asyncio.Queue = asyncio.Queue(maxsize=10)

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


def _pick_carnumber_image() -> str | None:
    """data/numberplate/에 아직 저장되지 않은 carnumber 이미지를 랜덤 선택.

    이미 numberplate 폴더에 동일 번호판 파일이 존재하면 제외한다.
    모두 사용된 경우 전체에서 선택한다.
    """
    images = _get_carnumber_images()
    if not images:
        return None

    candidates = [
        p for p in images
        if not os.path.exists(
            os.path.join("data/numberplate", os.path.splitext(os.path.basename(p))[0] + ".jpg")
        )
    ]
    if not candidates:
        candidates = images  # 전부 사용된 경우 전체에서 선택

    return random.choice(candidates)


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


def _inference_loop(model, meta_queue, event_queue, lock, stop_event,
                    shared, shared_lock, safe_put, process_headless,
                    vehicle_history_ref, MAX_PLAUSIBLE_SPEED):
    """[Thread 1] YOLO 추론 + 과속 감지 — 블라킹 허용, 공유 상태 업데이트"""
    from multiprocessing import shared_memory as _shm_mod
    _infer_counter = 0
    _last_results = None

    while not stop_event.is_set():
        try:
            try:
                meta = meta_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            existing_shm = _shm_mod.SharedMemory(name=meta['shm_name'])
            try:
                with lock:
                    frame = np.ndarray(meta['shape'], dtype=meta['dtype'],
                                       buffer=existing_shm.buf).copy()
            finally:
                existing_shm.close()

            # 2프레임에 1회만 YOLO 추론 — 나머지는 이전 결과 재사용으로 CPU 부하 절반 감소
            _infer_counter += 1
            _is_new_result = True
            if _infer_counter % 2 == 0 and _last_results is not None:
                results = _last_results
                _is_new_result = False
            else:
                results = model.track(frame, persist=True, tracker="bytetrack.yaml",
                                      verbose=False, imgsz=settings.INFERENCE_IMGSZ,
                                      conf=settings.CONF_THRESHOLD,
                                      classes=settings.TARGET_CLASSES)
                _last_results = results

            # [과속 감지] 새 추론 결과일 때만 속도 업데이트 — 재사용 프레임은 EMA 왜곡 방지
            speeding_events = process_headless(results) if _is_new_result else []

            # 과속 감지된 차량에 대해 carnumber 랜덤 이미지 선정 후 이벤트 큐에 적재
            for evt in speeding_events:
                src_path = _pick_carnumber_image()
                if not src_path:
                    logger.warning("[InferThread] carnumber 이미지 없음. 과속 이벤트 스킵.")
                    continue
                evt["payload"]["src_image_path"] = src_path
                safe_put({"type": "SPEEDING_VIOLATION", "payload": evt["payload"]})

            # vehicle_history 스냅샷 생성 (RenderThread와 동시 접근 방지)
            snapshot = {tid: dict(data) for tid, data in vehicle_history_ref.items()}

            # 공유 상태 원자적 업데이트
            with shared_lock:
                shared["results"] = results
                shared["raw_frame"] = frame
                shared["frame_shape"] = frame.shape
                shared["vehicle_snapshot"] = snapshot

        except Exception as e:
            logger.error(f"[InferThread] 예외 발생 (계속 실행): {e}", exc_info=True)
            time.sleep(0.1)  # 연속 예외 폭발 방지


def _render_loop(mjpeg_queue, stop_event, shared, shared_lock, MAX_PLAUSIBLE_SPEED):
    """[Thread 2] 25fps 독립 렌더링 루프 — YOLO 추론 속도와 무관하게 항상 프레임 공급"""
    _frame_interval = 1.0 / settings.STREAM_FPS_LIMIT  # 0.04s (25fps)
    _no_signal_frame = None

    def _make_no_signal_frame():
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "Waiting for stream...", (140, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)
        _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return buf.tobytes()

    while not stop_event.is_set():
        _t0 = time.time()
        try:
            with shared_lock:
                results     = shared["results"]
                frame_shape = shared["frame_shape"]
                v_snapshot  = shared["vehicle_snapshot"]

            if results is None:
                # 초기 기동: YOLO 결과 아직 없음
                if _no_signal_frame is None:
                    _no_signal_frame = _make_no_signal_frame()
                frame_bytes = _no_signal_frame
            else:
                # [Web Demo] YOLO 박스 오버레이 렌더링
                annotated_frame = results[0].plot(labels=False)
                resized_frame = cv2.resize(annotated_frame, (640, 480))

                # [과속 오버레이] 각 차량 bbox 위에 속도 텍스트 표시 (스냅샷 사용)
                if results[0].boxes and results[0].boxes.id is not None:
                    id_list = results[0].boxes.id.int().cpu().tolist()
                    scale_x = 640 / frame_shape[1]
                    scale_y = 480 / frame_shape[0]
                    for i, track_id in enumerate(id_list):
                        data = v_snapshot.get(track_id)
                        if data is None:
                            continue
                        raw_speed = data.get("ema_speed", 0.0)
                        speed = min(raw_speed * settings.SPEED_SCALE_FACTOR, MAX_PLAUSIBLE_SPEED)
                        if speed < 50:
                            continue
                        box = results[0].boxes[i]
                        x_center, y_center, width, _ = box.xywh[0].tolist()
                        x_px = int((x_center - width / 2) * scale_x)
                        y_px = max(0, int(y_center * scale_y) - 10)
                        if speed >= 70:
                            color = (0, 0, 255)
                        elif speed >= 60:
                            color = (0, 220, 0)
                        else:
                            color = (255, 255, 255)
                        label = f"ID:{track_id} {speed:.0f}km/h"
                        cv2.putText(resized_frame, label, (x_px, y_px),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA)

                ret, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
                if not ret:
                    if _no_signal_frame is None:
                        _no_signal_frame = _make_no_signal_frame()
                    frame_bytes = _no_signal_frame
                else:
                    frame_bytes = buffer.tobytes()

            try:
                mjpeg_queue.put_nowait(frame_bytes)
            except queue.Full:
                try:
                    mjpeg_queue.get_nowait()
                    mjpeg_queue.put_nowait(frame_bytes)
                except (queue.Full, queue.Empty):
                    pass

        except Exception as e:
            logger.error(f"[RenderThread] 예외 발생 (계속 실행): {e}", exc_info=True)

        # 25fps 타이밍 보정 — 렌더링 소요 시간을 빼고 슬립
        elapsed = time.time() - _t0
        sleep_time = _frame_interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


def ai_inference_worker(meta_queue: Queue, event_queue: Queue, mjpeg_queue: Queue, lock: Lock, stop_event: Event):
    """[Process B] AI 추론(InferThread) + 렌더링(RenderThread) 분리 워커"""
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

    # Process B 스코프 공유 상태 (두 스레드가 공유)
    _shared = {
        "results": None,
        "raw_frame": None,
        "frame_shape": None,
        "vehicle_snapshot": {},
    }
    _shared_lock = threading.Lock()

    t_infer = threading.Thread(
        target=_inference_loop,
        args=(model, meta_queue, event_queue, lock, stop_event,
              _shared, _shared_lock, safe_put, process_headless_inference,
              vehicle_history, MAX_PLAUSIBLE_SPEED_KMH),
        name="InferThread",
        daemon=True,
    )
    t_render = threading.Thread(
        target=_render_loop,
        args=(mjpeg_queue, stop_event, _shared, _shared_lock, MAX_PLAUSIBLE_SPEED_KMH),
        name="RenderThread",
        daemon=True,
    )

    t_infer.start()
    t_render.start()
    logger.info("[AI Engine] InferThread + RenderThread 기동 완료.")

    t_infer.join()
    t_render.join()
    logger.info("[AI Engine] 프로세스 종료.")


async def _handle_speeding_violation(payload: dict):
    """과속 이벤트: carnumber 이미지에 OCR 실행 → webhook 전송"""
    payload["cameraId"] = vision_engine.camera_id
    src_path = payload.pop("src_image_path", None)
    if src_path:
        payload["srcImageUrl"] = f"carnumber/{os.path.basename(src_path)}"

    if src_path and os.path.exists(src_path):
        from services.ocr_storage import run_ocr_on_file  # lazy import: 메인 프로세스에서만 실행
        result = await run_ocr_on_file(src_path)
        plate = result["plate_number"]
        payload["plateNumber"] = plate
        payload["imageUrl"] = result["image_url"]   # "numberplate/filename.jpg" (프론트에서 prefix 추가)
        # 미인식/UNRECOGNIZED 번호판은 신뢰도 무관하게 수동 검토 필수
        if not plate or plate == "미인식" or plate.startswith("UNRECOGNIZED"):
            payload["needsReview"] = True
        else:
            payload["needsReview"] = result.get("needs_review", True)
        logger.info(f"[Speeding] OCR 완료 — 번호판: {plate} | 이미지: {result['image_url']} | 수동검토: {payload['needsReview']}")
    else:
        payload["plateNumber"] = "미인식"
        payload["imageUrl"] = None
        payload["needsReview"] = True
        logger.warning(f"[Speeding] carnumber 이미지 없음 — 미인식 처리")

    await webhook_client.send_violation(payload)


async def _handle_speeding_violation_safe(payload: dict):
    """예외 격리 래퍼: 과속 처리 실패가 이벤트 루프에 전파되지 않도록 보호"""
    try:
        await _handle_speeding_violation(payload)
    except Exception as e:
        logger.error(f"[Speeding] 위반 처리 예외: {e}")


async def _violation_worker():
    """과속 위반을 1개씩 순차 처리 — 동시 OCR 코루틴 누적을 차단하여 MJPEG 스트림 보호"""
    while True:
        payload = await _violation_queue.get()
        await _handle_speeding_violation_safe(payload)


class VisionEngine:
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.camera_id: str = settings.CAMERA_ID
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
        asyncio.create_task(_violation_worker())  # 단일 위반 처리 워커 기동
        while not self.stop_event.is_set():
            # 워커 프로세스 헬스체크 — 해상도 변경 등으로 프로세스 사망 시 자동 재시작
            if (self.reader_process and not self.reader_process.is_alive()) or \
               (self.ai_process and not self.ai_process.is_alive()):
                logger.warning("[Vision] 워커 프로세스 사망 감지 — 자동 재시작")
                self.restart(self.rtsp_url)
                await asyncio.sleep(3)
                continue

            try:
                event = self.event_queue.get_nowait()

                if event["type"] == "SPEEDING_VIOLATION":
                    # 위반 큐에 적재 → _violation_worker가 1개씩 순차 처리 (스트림 영향 없음)
                    try:
                        _violation_queue.put_nowait(event["payload"])
                    except asyncio.QueueFull:
                        logger.warning("[EventLoop] 위반 큐 포화(10개) — 이벤트 드롭")

            except queue.Empty:
                await asyncio.sleep(0.05)  # 이벤트 없으면 50ms 대기 — 스레드풀 미사용

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
            except queue.Empty: break
        while not self.mjpeg_queue.empty():
            try: self.mjpeg_queue.get_nowait()
            except queue.Empty: break
        self.start()


# 글로벌 인스턴스
vision_engine = VisionEngine(rtsp_url=settings.VIDEO_SOURCE_URL)
