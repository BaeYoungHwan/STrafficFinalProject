"""핵심 시뮬레이터 — 12대 센서값 생성 (벽시계 시간 기반)."""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime
from typing import Dict, List

from services.predictive.config import (
    ACCELERATION,
    FAULT_BEARING,
    FAULT_DIST,
    NORMAL_DIST,
    PATH_ACUTE,
    PATH_NATURAL,
    PATH_NORMAL,
    SPIKE_DURATION_MAX_SEC,
    SPIKE_DURATION_MIN_SEC,
    SPIKE_INTERVAL_MAX_SEC,
    SPIKE_INTERVAL_MIN_SEC,
)
from services.predictive.state import EquipmentState

logger = logging.getLogger(__name__)


class Simulator:
    """벽시계 시간 기반 시뮬레이터 — 틱 간격이 드리프트해도 가상 시간 정확히 유지."""

    def __init__(self, states: List[EquipmentState]):
        self.states = states
        self.start_time = datetime.now()
        self.last_tick_time = self.start_time
        self.tick_count = 0

    # ------------------------------------------------------------------
    # 3층 변동 유틸 — 벽시계 시간 기반 phase
    # ------------------------------------------------------------------
    def _three_layer_variation(
        self,
        base: float,
        noise_sigma: float,
        diurnal_amp: float,
        load_amp: float,
        real_seconds_from_start: float,
    ) -> float:
        """base + Gaussian noise + diurnal drift(가상 24h) + load variation(실 5분)."""
        noise = random.gauss(0.0, noise_sigma)

        virtual_seconds = real_seconds_from_start * ACCELERATION
        diurnal_phase = (virtual_seconds % 86400.0) / 86400.0
        diurnal = diurnal_amp * math.sin(2 * math.pi * diurnal_phase)

        load_phase = (real_seconds_from_start % 300.0) / 300.0
        load = load_amp * math.sin(2 * math.pi * load_phase)

        return base + noise + diurnal + load

    def _interpolate(self, normal_base: float, fault_base: float, health_ratio: float) -> float:
        """제곱 보간: 초반엔 정상, 수명 후반에 급격히 고장 쪽으로 이동."""
        factor = (1.0 - health_ratio) ** 2
        return normal_base + factor * (fault_base - normal_base)

    # ------------------------------------------------------------------
    # 센서값 생성 (경로별)
    # ------------------------------------------------------------------
    def _generate_normal(self, real_sec: float) -> Dict[str, float]:
        return {
            feat: self._three_layer_variation(*params, real_sec)
            for feat, params in NORMAL_DIST.items()
        }

    def _generate_path1_natural_wear(self, state: EquipmentState, real_sec: float) -> Dict[str, float]:
        fault_dist = FAULT_DIST.get(state.planned_fault)
        if fault_dist is None:
            return self._generate_normal(real_sec)

        hr = state.health_ratio()
        factor = (1.0 - hr) ** 2
        result: Dict[str, float] = {}
        for feat in ("vibration", "temperature", "motor_current"):
            n_base, n_sigma, n_diurnal, n_load = NORMAL_DIST[feat]
            f_base, f_sigma, _, _ = fault_dist[feat]
            base = self._interpolate(n_base, f_base, hr)
            sigma = n_sigma + factor * (f_sigma - n_sigma)
            result[feat] = self._three_layer_variation(base, sigma, n_diurnal, n_load, real_sec)
        return result

    def _generate_path2_acute(
        self, state: EquipmentState, delta_sec: float, real_sec: float,
    ) -> Dict[str, float]:
        """Path② — 평상은 정상, 이벤트 시 고장 분포 스파이크."""
        if not state.spike_active:
            if state.next_spike_in_sec > 0:
                state.next_spike_in_sec -= delta_sec
            else:
                state.spike_active = True
                state.spike_remaining_sec = random.uniform(
                    SPIKE_DURATION_MIN_SEC, SPIKE_DURATION_MAX_SEC
                )
                logger.debug(
                    "[Simulator] eq_id=%s 스파이크 시작 duration=%.1fs",
                    state.equipment_id, state.spike_remaining_sec,
                )

        if state.spike_active:
            if state.spike_remaining_sec > 0:
                state.spike_remaining_sec -= delta_sec
                fault_dist = FAULT_DIST.get(state.planned_fault, FAULT_DIST[FAULT_BEARING])
                return {
                    feat: self._three_layer_variation(*fault_dist[feat], real_sec)
                    for feat in ("vibration", "temperature", "motor_current")
                }
            else:
                state.spike_active = False
                state.next_spike_in_sec = random.uniform(
                    SPIKE_INTERVAL_MIN_SEC, SPIKE_INTERVAL_MAX_SEC
                )
                logger.debug("[Simulator] eq_id=%s 스파이크 종료", state.equipment_id)

        return self._generate_normal(real_sec)

    # ------------------------------------------------------------------
    # 단일 장비 틱 처리
    # ------------------------------------------------------------------
    def _tick_equipment(
        self, state: EquipmentState, delta_sec: float, real_sec: float,
    ) -> Dict:
        if state.path == PATH_NORMAL:
            sensors = self._generate_normal(real_sec)
        elif state.path == PATH_NATURAL:
            rul_decrease_days = delta_sec * ACCELERATION / 86400.0
            state.rul = max(0.0, state.rul - rul_decrease_days)
            sensors = self._generate_path1_natural_wear(state, real_sec)
        elif state.path == PATH_ACUTE:
            sensors = self._generate_path2_acute(state, delta_sec, real_sec)
        else:
            sensors = self._generate_normal(real_sec)

        return {
            "equipmentId": state.equipment_id,
            "vibration": round(sensors["vibration"], 3),
            "temperature": round(sensors["temperature"], 2),
            "motorCurrent": round(sensors["motor_current"], 2),
            "rul": round(state.rul, 2),
            "recordedAt": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 한 틱 전체 생성
    # ------------------------------------------------------------------
    def generate_tick(self) -> List[Dict]:
        now = datetime.now()
        delta_sec = (now - self.last_tick_time).total_seconds()
        real_sec = (now - self.start_time).total_seconds()

        items = [self._tick_equipment(state, delta_sec, real_sec) for state in self.states]

        self.last_tick_time = now
        self.tick_count += 1
        return items
