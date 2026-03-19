import logging
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CongestionEngine:
    """
    교차로 ROI 진입/이탈 이벤트를 기반으로 혼잡도를 실시간 산출한다.

    혼잡도 기준:
        - 0~5대  : SMOOTH  (원활)
        - 6~15대 : SLOW    (서행)
        - 16대+  : CONGESTED (혼잡)
    """

    THRESHOLD_SMOOTH = 5
    THRESHOLD_SLOW = 15

    def __init__(self):
        self._active_vehicles: set = set()
        self._total_entries: int = 0
        self._total_exits: int = 0
        self._last_updated: datetime | None = None

    async def record_entry(self, track_id: int):
        self._active_vehicles.add(track_id)
        self._total_entries += 1
        self._last_updated = datetime.now(timezone.utc)

    async def record_exit(self, track_id: int):
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

# ─────────────────────────────────────────────
# 스케줄러 진입점 (main.py의 lifespan에서 호출)
# ─────────────────────────────────────────────

_periodic_task: asyncio.Task | None = None


async def _periodic_log():
    """30초마다 혼잡도 상태를 로그에 출력하는 백그라운드 태스크."""
    while True:
        await asyncio.sleep(30)
        status = await congestion_engine.get_status()
        logger.info(
            "[Aggregator] Congestion status — level: %s, active: %d",
            status["congestion_level"],
            status["active_vehicles"],
        )


def start_aggregators():
    """main.py lifespan 시작 시 호출. 백그라운드 집계 태스크를 등록한다."""
    global _periodic_task
    _periodic_task = asyncio.create_task(_periodic_log())
    logger.info("[Aggregator] Started congestion monitor.")


async def stop_aggregators():
    """main.py lifespan 종료 시 호출. 태스크를 안전하게 해제한다."""
    global _periodic_task
    if _periodic_task:
        _periodic_task.cancel()
        try:
            await _periodic_task
        except asyncio.CancelledError:
            pass
    logger.info("[Aggregator] Stopped.")
