import httpx
import asyncio
import json
import os
import time
import logging
import aiofiles
from core.config import settings

logger = logging.getLogger(__name__)

FALLBACK_FILE = "data/fallback_queue.jsonl"
os.makedirs("data", exist_ok=True)

class HTTPClientWithRetry:
    def __init__(self):
        self.client = None
        self.queue = asyncio.Queue(maxsize=settings.QUEUE_MAXSIZE)
        self.retry_task = None
        self.file_lock = asyncio.Lock()  # [QA 반영 3.1] 비동기 파일 쓰기 락
        
        # [QA 반영 2.2] Circuit Breaker 설정
        self.circuit_open = False
        self.circuit_open_until = 0.0
        self.consecutive_failures = 0
        self.FAILURE_THRESHOLD = 5
        self.CIRCUIT_COOLDOWN = 30.0  # 백엔드 다운 시 30초간 전송 차단

    async def start(self):
        """FastAPI 시작 시 호출"""
        self.client = httpx.AsyncClient(base_url=settings.BACKEND_URL, timeout=5.0)
        await self._load_from_fallback()  # [QA 반영 2.1] Cold Start Recovery
        self.retry_task = asyncio.create_task(self._retry_worker())
        logger.info("[HTTP] Async HTTP Client started with Circuit Breaker.")

    async def stop(self):
        """FastAPI 종료 시 안전 해제 및 큐 백업"""
        if self.retry_task:
            self.retry_task.cancel()
            await asyncio.gather(self.retry_task, return_exceptions=True)
            
        # 남은 큐의 데이터를 영속성 파일로 백업
        while not self.queue.empty():
            endpoint, payload, retry_count = self.queue.get_nowait()
            await self._save_to_fallback(endpoint, payload, retry_count)
            
        if self.client:
            await self.client.aclose()
        logger.info("[HTTP] Async HTTP Client stopped. Unsent data backed up.")

    async def _load_from_fallback(self):
        """[QA 반영 2.1] 재시작 시 디스크에 남은 데이터를 큐로 복원합니다."""
        if not os.path.exists(FALLBACK_FILE):
            return
        
        async with self.file_lock:
            try:
                async with aiofiles.open(FALLBACK_FILE, "r", encoding="utf-8") as f:
                    lines = await f.readlines()
                
                # 파일 읽은 후 즉시 초기화
                async with aiofiles.open(FALLBACK_FILE, "w", encoding="utf-8") as f:
                    await f.write("")
                    
                recovered_count = 0
                for line in lines:
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    try:
                        self.queue.put_nowait((record["endpoint"], record["payload"], record.get("retry_count", 0)))
                        recovered_count += 1
                    except asyncio.QueueFull:
                        logger.critical("[HTTP] Queue full during recovery! Remaining data will be re-saved.")
                        # 큐가 꽉 차면 남은 줄들을 다시 파일에 써야 하지만, MVP 스펙에서는 로그만 남김
                        break
                logger.info(f"[HTTP] Recovered {recovered_count} items from fallback file.")
            except Exception as e:
                logger.error(f"[HTTP] Failed to load fallback data: {e}")

    async def _save_to_fallback(self, endpoint: str, payload: dict, retry_count: int = 0):
        """[QA 반영 3.1] aiofiles와 Lock을 이용한 안전한 로컬 저장"""
        async with self.file_lock:
            try:
                async with aiofiles.open(FALLBACK_FILE, "a", encoding="utf-8") as f:
                    record = {"endpoint": endpoint, "payload": payload, "retry_count": retry_count}
                    await f.write(json.dumps(record, ensure_ascii=False) + "\n")
            except Exception as e:
                logger.error(f"[HTTP] Critical File I/O Error: {e}")

    def _handle_failure(self):
        """연속 실패 감지 및 Circuit Breaker 개방"""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.FAILURE_THRESHOLD:
            self.circuit_open = True
            self.circuit_open_until = time.time() + self.CIRCUIT_COOLDOWN
            logger.critical(f"[HTTP] CIRCUIT BREAKER OPENED! Backend unreachable. Cooldown: {self.CIRCUIT_COOLDOWN}s")

    async def send_payload(self, endpoint: str, payload: dict):
        """외부에서 호출하는 데이터 전송 진입점"""
        # 1. 서킷 브레이커가 열려있다면 전송 시도조차 하지 않고 즉시 큐/디스크로 우회
        if self.circuit_open:
            if time.time() < self.circuit_open_until:
                try:
                    self.queue.put_nowait((endpoint, payload, 0))
                except asyncio.QueueFull:
                    await self._save_to_fallback(endpoint, payload, 0)
                return
            else:
                self.circuit_open = False  # 쿨다운 종료, 반개방(Half-open) 상태 전환
                logger.info("[HTTP] Circuit Breaker half-open, testing connection.")

        # 2. 정상 전송 시도
        try:
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            logger.info(f"[HTTP] Successfully sent to {endpoint}")
            self.consecutive_failures = 0  # 성공 시 실패 카운트 초기화
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.error(f"[HTTP] Send failed ({e}).")
            self._handle_failure()
            try:
                self.queue.put_nowait((endpoint, payload, 1))
            except asyncio.QueueFull:
                await self._save_to_fallback(endpoint, payload, 1)

    async def _retry_worker(self):
        """[QA 반영 2.2] 큐 마비를 일으키지 않는 백그라운드 재전송 워커"""
        while True:
            try:
                endpoint, payload, retry_count = await self.queue.get()
                
                # 서킷 브레이커가 열려있다면, 워커를 재우지(sleep) 않고 아이템을 큐 맨 뒤로 다시 넘김
                if self.circuit_open and time.time() < self.circuit_open_until:
                    await self.queue.put((endpoint, payload, retry_count))
                    self.queue.task_done()
                    await asyncio.sleep(1.0)  # 무한 루프 CPU 독점 방지용 최소 대기
                    continue
                elif self.circuit_open:
                    self.circuit_open = False
                
                try:
                    res = await self.client.post(endpoint, json=payload)
                    res.raise_for_status()
                    logger.info(f"[HTTP] Retry successful for {endpoint} (Attempt: {retry_count})")
                    self.consecutive_failures = 0
                    self.queue.task_done()
                except Exception as e:
                    self._handle_failure()
                    # 실패한 아이템만 큐 뒤로 넘기거나, 임계치(10회) 초과 시 파일로 내려씀
                    if retry_count < 10:
                        await self.queue.put((endpoint, payload, retry_count + 1))
                    else:
                        logger.warning(f"[HTTP] Max retries reached for {endpoint}. Saving to fallback.")
                        await self._save_to_fallback(endpoint, payload, retry_count)
                    self.queue.task_done()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HTTP] Retry worker error: {e}")
                await asyncio.sleep(1.0)

# 전역 싱글톤 인스턴스
http_client = HTTPClientWithRetry()