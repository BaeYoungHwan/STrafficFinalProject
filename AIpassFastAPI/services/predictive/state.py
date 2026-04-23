"""12대 장비 상태 + DB 초기 RUL 로더 (벽시계 시간 기반)."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import date
from typing import List

import psycopg2

from services.predictive.config import (
    EQUIPMENT_PLAN,
    PATH_ACUTE,
    PATH_NORMAL,
    SPIKE_INTERVAL_MAX_SEC,
    SPIKE_INTERVAL_MIN_SEC,
)

logger = logging.getLogger(__name__)


@dataclass
class EquipmentState:
    equipment_id: int
    path: str
    planned_fault: str
    rul: float
    initial_rul: float

    # Path② 급성 이벤트 상태
    spike_active: bool = False
    spike_remaining_sec: float = 0.0
    next_spike_in_sec: float = 0.0

    def health_ratio(self) -> float:
        """RUL 기반 건강도. 1.0(신품) ~ 0.0(수명끝)."""
        return max(0.0, min(1.0, self.rul / 300.0))


def load_initial_states(
    db_host: str = "localhost",
    db_port: int = 5432,
    db_name: str = "aipass",
    db_user: str = "postgres",
    db_password: str = "1234",
) -> List[EquipmentState]:
    """DB equipment 테이블에서 12대 초기 상태 로드."""
    conn = psycopg2.connect(
        host=db_host, port=db_port, dbname=db_name,
        user=db_user, password=db_password,
    )
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT equipment_id, installation_date FROM equipment "
            "WHERE equipment_id BETWEEN 1 AND 12 ORDER BY equipment_id"
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    today = date.today()
    states: List[EquipmentState] = []
    for eq_id, install_date in rows:
        if eq_id not in EQUIPMENT_PLAN:
            logger.warning("[Simulator] EQUIPMENT_PLAN 누락 eq_id=%s, 정상으로 처리", eq_id)
            path, planned = PATH_NORMAL, "NORMAL"
        else:
            path, planned = EQUIPMENT_PLAN[eq_id]

        elapsed_days = (today - install_date).days if install_date else 0
        rul = max(0.0, 300.0 - elapsed_days)

        state = EquipmentState(
            equipment_id=eq_id,
            path=path,
            planned_fault=planned,
            rul=rul,
            initial_rul=rul if rul > 0 else 300.0,
        )

        if path == PATH_ACUTE:
            state.next_spike_in_sec = random.uniform(
                SPIKE_INTERVAL_MIN_SEC, SPIKE_INTERVAL_MAX_SEC
            )

        states.append(state)

    if len(states) != 12:
        logger.warning("[Simulator] 장비 수가 12 가 아님: %d", len(states))

    logger.info("[Simulator] 초기 상태 로딩 완료 — %d대", len(states))
    for s in states:
        logger.info(
            "  eq_id=%s path=%s plan=%s rul=%.1f",
            s.equipment_id, s.path, s.planned_fault, s.rul,
        )
    return states


def reset_state(state: EquipmentState) -> None:
    """자동 정비 완료 후 상태 리셋."""
    state.rul = 300.0
    state.initial_rul = 300.0
    state.spike_active = False
    state.spike_remaining_sec = 0.0
    if state.path == PATH_ACUTE:
        state.next_spike_in_sec = random.uniform(
            SPIKE_INTERVAL_MIN_SEC, SPIKE_INTERVAL_MAX_SEC
        )
    logger.info("[Simulator] eq_id=%s 상태 리셋 완료", state.equipment_id)
