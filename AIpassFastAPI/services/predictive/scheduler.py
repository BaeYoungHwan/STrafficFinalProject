"""시뮬레이터 스케줄러 — 15초 주기 루프 + END_TIME 자동 종료."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from core.config import settings
from services.predictive.client import predictive_client
from services.predictive.config import DEFAULT_END_TIME_ISO, TICK_SECONDS
from services.predictive.simulator import Simulator
from services.predictive.state import load_initial_states, reset_state

logger = logging.getLogger(__name__)

_simulator: Optional[Simulator] = None
_loop_task: Optional[asyncio.Task] = None
_end_time: Optional[datetime] = None


def _resolve_end_time() -> Optional[datetime]:
    """env SIMULATOR_END_TIME > config.DEFAULT_END_TIME_ISO. None/'none'/'' → 무한 실행."""
    raw = os.environ.get("SIMULATOR_END_TIME")
    if raw is None:
        raw = DEFAULT_END_TIME_ISO
    if not raw or (isinstance(raw, str) and raw.lower() in ("none", "never", "off")):
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        logger.warning("[Simulator] SIMULATOR_END_TIME 파싱 실패 '%s' — 무한 실행", raw)
        return None


async def _simulator_loop() -> None:
    """15초 주기 메인 루프. END_TIME 도달 시 자동 종료."""
    global _simulator
    assert _simulator is not None

    logger.info("[Simulator] 루프 시작 (END_TIME=%s)", _end_time)
    tick = 0

    while True:
        now = datetime.now()
        if _end_time and now >= _end_time:
            logger.info("[Simulator] END_TIME 도달 — 루프 종료 (총 %d tick)", tick)
            break

        try:
            # 1. 한 틱 데이터 생성 (로컬 CRITICAL 락/리셋은 simulator 내부 처리)
            items = _simulator.generate_tick()

            # 2. Spring Boot 배치 전송 (단순 수신 + DB 저장)
            ok = await predictive_client.send_batch(items)
            if not ok:
                logger.debug("[Simulator] tick=%d 전송 실패 (계속 진행)", tick)

            if tick % 20 == 0:
                total_sent = tick * len(_simulator.states)
                logger.info("[Simulator] tick=%d total_sent=%d", tick, total_sent)

        except Exception as e:
            logger.error("[Simulator] 틱 처리 오류 tick=%d: %s", tick, repr(e))

        tick += 1
        await asyncio.sleep(TICK_SECONDS)

    logger.info("[Simulator] 종료 완료.")


async def start_simulator() -> None:
    """FastAPI lifespan 에서 호출."""
    global _simulator, _loop_task, _end_time

    if os.environ.get("SIMULATOR_ENABLED", "false").lower() not in ("1", "true", "yes", "on"):
        logger.info("[Simulator] SIMULATOR_ENABLED 꺼짐 — 가동 건너뜀")
        return

    if _loop_task is not None and not _loop_task.done():
        logger.warning("[Simulator] 이미 실행 중")
        return

    _end_time = _resolve_end_time()
    logger.info("[Simulator] 시작 요청 (END_TIME=%s)", _end_time)

    try:
        states = load_initial_states(
            db_host=settings.DB_HOST,
            db_port=settings.DB_PORT,
            db_name=settings.DB_NAME,
            db_user=settings.DB_USER,
            db_password=settings.DB_PASSWORD,
        )
    except Exception as e:
        logger.error("[Simulator] 초기 상태 로드 실패: %s", repr(e))
        return

    _simulator = Simulator(states)
    await predictive_client.start()
    _loop_task = asyncio.create_task(_simulator_loop(), name="simulator_loop")
    logger.info("[Simulator] 가동 완료 — %d대 장비", len(states))


def reset_equipment(equipment_id: int) -> bool:
    if _simulator is None:
        return False
    for state in _simulator.states:
        if state.equipment_id == equipment_id:
            reset_state(state)
            return True
    return False


async def stop_simulator() -> None:
    """FastAPI lifespan 종료 시 호출."""
    global _loop_task
    if _loop_task is not None and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
    await predictive_client.stop()
    logger.info("[Simulator] 정리 완료")
