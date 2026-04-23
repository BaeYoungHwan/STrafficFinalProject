"""ML 기반 판정 — anomaly(binary) + fault(3-class) + risk_level(규칙 유지)."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import joblib
import numpy as np

from services.predictive.config import FAULT_NORMAL

# 규칙 기반 risk_level 계산용 임계값 (judge.py 로컬 상수)
VIB_WARN = 0.8
VIB_DANGER = 2.0
TEMP_WARN = 60.0
TEMP_DANGER = 80.0
CUR_WARN = 20.0
CUR_DANGER = 35.0

_MODELS_DIR = Path(__file__).parent / "models"

# 모듈 로드 시 1회: 모델/인코더 싱글톤
_anomaly_model = joblib.load(_MODELS_DIR / "anomaly_model.joblib")
_fault_model = joblib.load(_MODELS_DIR / "fault_model.joblib")
_fault_label_encoder = joblib.load(_MODELS_DIR / "fault_label_encoder.joblib")

_FAULT_CLASSES = [str(c) for c in _fault_label_encoder.classes_]  # ["BEARING_FAULT","COMPOUND_FAULT","MOTOR_FAULT"]


def judge(
    vibration: float,
    temperature: float,
    motor_current: float,
) -> Tuple[bool, float, str, str]:
    """
    반환: (is_anomaly, anomaly_score, fault_type, risk_level)

    - 이상탐지: anomaly_model (XGB binary)
    - 고장분류: fault_model (XGB 3-class, 이상일 때만 호출)
    - anomaly_score: rule_judge 공식 유지 (각 센서 주의→위험 진행률 max, 포화 1.0)
    - risk_level: rule_judge 카운트 로직 유지 (danger_count/warn_count 기반)
    """

    # 영역 플래그 (risk_level 규칙 계산에 사용)
    vib_warn = vibration >= VIB_WARN
    vib_danger = vibration >= VIB_DANGER
    temp_warn = temperature >= TEMP_WARN
    temp_danger = temperature >= TEMP_DANGER
    cur_warn = motor_current >= CUR_WARN
    cur_danger = motor_current >= CUR_DANGER

    # anomaly_score — 기존 공식 유지 (연속 값이라 UI/로그에서 해석 용이)
    vib_score = max(0.0, (vibration - VIB_WARN) / (VIB_DANGER - VIB_WARN))
    temp_score = max(0.0, (temperature - TEMP_WARN) / (TEMP_DANGER - TEMP_WARN))
    cur_score = max(0.0, (motor_current - CUR_WARN) / (CUR_DANGER - CUR_WARN))
    anomaly_score = float(min(1.0, max(vib_score, temp_score, cur_score)))

    # ── 이상탐지 (ML) ──
    features = np.array([[vibration, temperature, motor_current]], dtype=float)
    is_anomaly = bool(int(_anomaly_model.predict(features)[0]))

    # ── 고장분류 ──
    if not is_anomaly:
        fault_type = FAULT_NORMAL
    else:
        fault_idx = int(_fault_model.predict(features)[0])
        fault_type = _FAULT_CLASSES[fault_idx]

    # ── risk_level — 규칙 유지 (danger_count/warn_count) ──
    danger_count = int(vib_danger) + int(temp_danger) + int(cur_danger)
    warn_count = int(vib_warn) + int(temp_warn) + int(cur_warn) - danger_count

    if warn_count == 0 and danger_count == 0:
        risk_level = "LOW"
    elif warn_count >= 1 and danger_count == 0:
        risk_level = "MEDIUM"
    elif danger_count == 1:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    return is_anomaly, anomaly_score, fault_type, risk_level
