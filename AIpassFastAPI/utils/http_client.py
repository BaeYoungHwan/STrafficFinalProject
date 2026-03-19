import logging
import asyncio
import httpx
from core.config import settings

logger = logging.getLogger(__name__)


class HttpClient:
    """Spring Boot 백엔드로 이벤트 페이로드를 전송하는 HTTP 클라이언트 (비동기 retry 큐 포함)"""

    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._retry_queue: asyncio.Queue = asyncio.Queue(maxsize=settings.QUEUE_MAXSIZE)
        self._worker_task: asyncio.Task | None = None

    async def start(self):
        self._client = httpx.AsyncClient(timeout=5.0)
        self._worker_task = asyncio.create_task(self._retry_worker())
        logger.info("[HttpClient] Started. Backend URL: %s", settings.BACKEND_URL)

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
        logger.info("[HttpClient] Stopped. Remaining queue size: %d", self._retry_queue.qsize())

    async def send_payload(self, path: str, payload: dict):
        """백엔드로 POST 전송. 실패 시 retry 큐에 적재."""
        url = settings.BACKEND_URL.rstrip("/") + path
        try:
            response = await self._client.post(url, json=payload)
            if response.status_code < 300:
                logger.info("[HttpClient] Sent OK → %s", path)
            else:
                logger.warning("[HttpClient] Non-2xx %d → %s. Queuing for retry.", response.status_code, path)
                await self._enqueue(path, payload)
        except Exception as e:
            logger.warning("[HttpClient] Send failed (%s). Queuing for retry.", e)
            await self._enqueue(path, payload)

    async def _enqueue(self, path: str, payload: dict):
        try:
            self._retry_queue.put_nowait({"path": path, "payload": payload, "retries": 0})
        except asyncio.QueueFull:
            logger.error("[HttpClient] Retry queue full. Dropping event for %s", path)

    async def _retry_worker(self):
        """백그라운드 retry 워커 — 3초마다 큐에서 꺼내 재전송 시도."""
        while True:
            try:
                item = await self._retry_queue.get()
                path = item["path"]
                payload = item["payload"]
                retries = item["retries"]

                if retries >= 5:
                    logger.error("[HttpClient] Max retries exceeded for %s. Dropping.", path)
                    continue

                await asyncio.sleep(3 * (retries + 1))  # 지수 백오프 근사
                url = settings.BACKEND_URL.rstrip("/") + path
                try:
                    response = await self._client.post(url, json=payload)
                    if response.status_code < 300:
                        logger.info("[HttpClient] Retry OK (attempt %d) → %s", retries + 1, path)
                    else:
                        item["retries"] += 1
                        await self._retry_queue.put(item)
                except Exception as e:
                    logger.warning("[HttpClient] Retry failed (attempt %d): %s", retries + 1, e)
                    item["retries"] += 1
                    await self._retry_queue.put(item)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("[HttpClient] Worker error: %s", e)


http_client = HttpClient()
