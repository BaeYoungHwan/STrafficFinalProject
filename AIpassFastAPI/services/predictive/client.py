"""Spring Boot REST 클라이언트 — 배치 ingest raw 전송."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import httpx

from core.config import settings
from services.predictive.config import INGEST_PATH

logger = logging.getLogger(__name__)


class PredictiveClient:
    """시뮬레이터 → Spring Boot 전용 비동기 HTTP 클라이언트."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        self.base_url = base_url or settings.BACKEND_URL
        self.timeout = httpx.Timeout(timeout)
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("[PredictiveClient] 시작 — base_url=%s", self.base_url)

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("[PredictiveClient] 종료")

    async def send_batch(self, items: List[Dict]) -> bool:
        """POST /api/sensor/ingest — 24건 배치 raw 전송."""
        if not self._client:
            logger.error("[PredictiveClient] 클라이언트 미초기화")
            return False

        url = f"{self.base_url}{INGEST_PATH}"
        try:
            resp = await self._client.post(url, json={"items": items})
            resp.raise_for_status()
            return True
        except httpx.ConnectError:
            logger.warning("[PredictiveClient] Spring Boot 미연결 — 이 틱 건너뜀")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(
                "[PredictiveClient] ingest HTTP %s — %s",
                e.response.status_code, e.response.text[:200],
            )
            return False
        except Exception as e:
            logger.error("[PredictiveClient] ingest 실패: %s", repr(e))
            return False


# 싱글톤
predictive_client = PredictiveClient()
