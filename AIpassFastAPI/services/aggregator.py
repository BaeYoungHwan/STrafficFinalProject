import logging
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CongestionEngine:
    """
    교차로 ROI 진입/이탈 이벤트를 기반으로 혼잡도를 실시간 산출한다.

    혼잡도 기준:
        0~5대   : SMOOTH   (원활)
        6~15대  : SLOW     (서행)
        16대+   : CONGESTED (혼잡)
    """

    THRESHOLD_SMOOTH = 5
    THRESHOLD_SLOW = 15

    def __init__(self):
        self._active_vehicles: set = set()
        self._total_entries: int = 0
        self._total_exits: int = 0
        self._last_updated: datetime | None = None

    # sync로 변경 — 내부에 await 없음, 불필요한 코루틴 오버헤드 제거
    def record_entry(self, track_id: int) -> None:
        self._active_vehicles.add(track_id)
        self._total_entries += 1
        self._last_updated = datetime.now(timezone.utc)

    def record_exit(self, track_id: int) -> None:
        self._active_vehicles.discard(track_id)
        self._total_exits += 1
        self._last_updated = datetime.now(timezone.utc)

    async def get_status(self) -> dict:
        count = len(self._active_vehicles)
        if count <= self.THRESHOLD_SMOOTH:
            level = "SMOOTH"
        elif count <= self.THRESHOLD_SLOW:
            level = "SLOW"
        else:
            level = "CONGESTED"

        return {
            "active_vehicles": count,
            "congestion_level": level,
            "total_entries": self._total_entries,
            "total_exits": self._total_exits,
            "last_updated": self._last_updated.isoformat() if self._last_updated else None,
        }


congestion_engine = CongestionEngine()

# ─────────────────────────────────────────────────────────────
# 스케줄러 진입점 (main.py의 lifespan에서 호출)
# ─────────────────────────────────────────────────────────────

_tasks: list[asyncio.Task] = []


async def _periodic_log():
    """30초마다 혼잡도 상태를 로그에 출력."""
    while True:
        await asyncio.sleep(30)
        status = await congestion_engine.get_status()
        logger.info(
            "[Aggregator] Congestion — level: %s, active: %d",
            status["congestion_level"],
            status["active_vehicles"],
        )


async def _dlq_retry_loop():
    """5분마다 DLQ(미전송 파일) 재전송 시도."""
    await asyncio.sleep(60)  # 서버 완전 기동 후 시작
    while True:
        try:
            from services.webhook_client import webhook_client
            await webhook_client.retry_failed_payloads()
        except Exception as e:
            logger.warning("[Aggregator] DLQ retry error: %s", e)
        await asyncio.sleep(300)


def start_aggregators():
    global _tasks
    _tasks = [
        asyncio.create_task(_periodic_log()),
        asyncio.create_task(_dlq_retry_loop()),
    ]
    logger.info("[Aggregator] Started (congestion monitor + DLQ retry).")


async def stop_aggregators():
    for task in _tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _tasks.clear()
    logger.info("[Aggregator] Stopped.")
