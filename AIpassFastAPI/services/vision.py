import cv2
import time
import logging
import numpy as np
import queue
import asyncio
import multiprocessing
from multiprocessing import Process, Queue, shared_memory, Lock, Event

from ultralytics import YOLO
from core.config import settings

logger = logging.getLogger(__name__)

def video_reader_worker(rtsp_url: str, meta_queue: Queue, lock: Lock, stop_event: Event):
    """
    [독립 프로세스] 무결점(Race-condition free) OpenCV 프레임 수집 워커
    """
    cap = None
    shm = None
    try:
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            logger.error(f"[Vision] Failed to open stream: {rtsp_url}")
            return

        logger.info(f"[Vision] Started reading stream from {rtsp_url}")
        
        # 첫 프레임 기반 SharedMemory 할당
        ret, frame = cap.read()
        if not ret:
            return
            
        shm_size = frame.nbytes
        shm = shared_memory.SharedMemory(create=True, size=shm_size)
        shm_name = shm.name
        
        # [QA 해결 2.2] Event 기반의 Graceful Shutdown 루프 적용
        while not stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning("[Vision] Stream disconnected. Attempting reconnect...")
                if cap:
                    cap.release() 
                time.sleep(2)
                cap = cv2.VideoCapture(rtsp_url)
                continue
            
            # [QA 해결 3.1] 재연결 시 해상도(바이트 크기) 변조 검증
            if frame.nbytes != shm_size:
                logger.error("[Vision] Resolution changed during reconnect! Exiting worker to prevent memory corruption.")
                break # 워커 종료 후 Engine에서 재시작 유도 필요
                
            shared_array = np.ndarray(frame.shape, dtype=frame.dtype, buffer=shm.buf)
            
            # [QA 해결 2.1] Lock을 통한 쓰기(Write) 동기화 보장
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
        # [QA 해결 2.2] terminate()를 피했기 때문에 OS 자원이 무조건 안전하게 해제됨
        logger.info("[Vision] Cleaning up OpenCV and SharedMemory resources...")
        if cap:
            cap.release()
        if shm:
            shm.close()
            shm.unlink()

class VisionEngine:
    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.meta_queue = Queue(maxsize=3)
        self.latest_annotated_frame = None
        self.reader_process = None
        
        # [QA 해결 2.1 & 2.2] 동기화 및 종료 신호 객체 생성
        self.lock = Lock()
        self.stop_event = Event()
        
        logger.info("[Vision] Loading YOLOv8 model...")
        self.model = YOLO("yolov8n.pt") 

    def start(self):
        self.stop_event.clear()
        self.reader_process = Process(
            target=video_reader_worker, 
            args=(self.rtsp_url, self.meta_queue, self.lock, self.stop_event), 
            daemon=True
        )
        self.reader_process.start()

    async def process_inference_loop(self):
        """메인 이벤트 루프 블로킹 방지를 위한 비동기 추론 루프"""
        try:
            meta = await asyncio.to_thread(self.meta_queue.get, True, 5.0)
        except queue.Empty:
            return
        except Exception as e:
            logger.error(f"Queue error: {e}")
            return

        def _read_shared_memory():
            """스레드 풀 내부에서 Lock을 쥐고 프레임을 복사해오는 안전한 함수"""
            existing_shm = shared_memory.SharedMemory(name=meta['shm_name'])
            try:
                # [QA 해결 2.1] Lock을 통한 읽기(Read) 동기화 보장
                with self.lock:
                    safe_frame = np.ndarray(meta['shape'], dtype=meta['dtype'], buffer=existing_shm.buf).copy()
                return safe_frame
            finally:
                existing_shm.close()

        # 데이터 오염 없이 안전하게 프레임 획득
        try:
            frame = await asyncio.to_thread(_read_shared_memory)
        except FileNotFoundError:
            return

        # 무거운 추론 작업 스레드 오프로딩
        results = await asyncio.to_thread(
            self.model.track, frame, persist=True, tracker="bytetrack.yaml", verbose=False
        )
        annotated_frame = results[0].plot()

        resized_frame = await asyncio.to_thread(
            cv2.resize, annotated_frame, (settings.STREAM_MAX_WIDTH, settings.STREAM_MAX_HEIGHT)
        )
        self.latest_annotated_frame = resized_frame

    def stop(self):
        """[QA 해결 2.2] OS 자원 누수 방지를 위한 Graceful Shutdown"""
        if self.reader_process and self.reader_process.is_alive():
            logger.info("[Vision] Sending stop signal to worker process...")
            self.stop_event.set() # 워커 루프 중단 신호
            self.reader_process.join(timeout=5) # 워커의 finally 블록 실행 대기
            if self.reader_process.is_alive():
                logger.warning("[Vision] Worker process did not terminate gracefully. Forcing kill.")
                self.reader_process.terminate() # 최후의 수단
                
vision_engine = VisionEngine(rtsp_url="0")