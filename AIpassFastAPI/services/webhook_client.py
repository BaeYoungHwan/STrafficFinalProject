import os
import json
import httpx
import logging
import asyncio
import aiofiles
from core.config import settings
from services.violation_cache import push as push_to_cache

logger = logging.getLogger(__name__)

os.makedirs("data", exist_ok=True)
FALLBACK_FILE = "data/fallback_queue.jsonl"


class WebhookClient:
    def __init__(self):
        self.target_url = f"{settings.BACKEND_URL}/api/enforcement/webhook"
        self.timeout = httpx.Timeout(3.0)
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    async def start(self):
        """persistent HTTP 클라이언트 초기화 (main.py lifespan에서 호출)."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("[Webhook] Client started. Target: %s", self.target_url)

    async def stop(self):
        """클라이언트 종료 (main.py lifespan에서 호출)."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("[Webhook] Client stopped.")

    async def _save_to_dlq(self, payload: dict):
        """전송 실패 시 DLQ 파일에 추가 (파일 I/O 정합성 보장)."""
        async with self._lock:
            async with aiofiles.open(FALLBACK_FILE, mode="a", encoding="utf-8") as f:
                await f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        logger.warning("[Webhook] DLQ 저장: %s", payload.get("eventId"))

    async def send_violation(self, payload: dict) -> bool:
        """위반 이벤트를 백엔드로 전송. 실패 시 DLQ 보관."""
        # 메모리 캐시에 즉시 저장 (순환 임포트 없이 violation_cache 직접 참조)
        push_to_cache(payload)

        if not self._client:
            logger.error("[Webhook] Client가 초기화되지 않았습니다. DLQ로 즉시 보냅니다.")
            await self._save_to_dlq(payload)
            return False

        try:
            response = await self._client.post(self.target_url, json=payload)
            response.raise_for_status()
            logger.info("[Webhook] 발송 성공: %s", payload.get("eventId"))
            return True
        except httpx.ConnectError as e:
            logger.error("[Webhook] Spring Boot 연결 실패 (서버 미실행 또는 포트 오류): %s", repr(e))
            await self._save_to_dlq(payload)
            return False
        except httpx.HTTPStatusError as e:
            logger.error("[Webhook] HTTP 오류 %s — %s", e.response.status_code, e.response.text[:200])
            await self._save_to_dlq(payload)
            return False
        except httpx.RequestError as e:
            logger.error("[Webhook] 요청 실패 (%s): %s", type(e).__name__, repr(e))
            await self._save_to_dlq(payload)
            return False

    async def retry_failed_payloads(self):
        """DLQ 재전송 (Read-Clear-Append 패턴으로 원자성 보장)."""
        if not os.path.exists(FALLBACK_FILE):
            return

        if not self._client:
            return

        # [Lock] 데이터 읽기 + 파일 비우기
        async with self._lock:
            async with aiofiles.open(FALLBACK_FILE, mode="r", encoding="utf-8") as f:
                lines = await f.readlines()
            if not lines:
                return
            async with aiofiles.open(FALLBACK_FILE, mode="w", encoding="utf-8") as f:
                pass  # 파일 비우기

        logger.info("[Webhook] DLQ 재전송 시작: %d건", len(lines))
        remaining = []

        # [No-Lock] 네트워크 전송 (새 이벤트는 비어있는 파일에 append 가능)
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
                response = await self._client.post(self.target_url, json=payload)
                response.raise_for_status()
                logger.info("[Webhook] DLQ 복구: %s", payload.get("eventId"))
                await asyncio.sleep(0.05)  # 서버 부하 분산
            except json.JSONDecodeError:
                logger.error("[Webhook] DLQ 파일 손상, 스킵: %s...", line[:50])
            except Exception as e:
                logger.warning("[Webhook] DLQ 재전송 실패, 재보관 (%s): %s", type(e).__name__, repr(e))
                remaining.append(line + "\n")

        # [Lock] 실패 건 재보관
        if remaining:
            async with self._lock:
                async with aiofiles.open(FALLBACK_FILE, mode="a", encoding="utf-8") as f:
                    await f.writelines(remaining)
            logger.warning("[Webhook] DLQ 재보관: %d건", len(remaining))


webhook_client = WebhookClient()
