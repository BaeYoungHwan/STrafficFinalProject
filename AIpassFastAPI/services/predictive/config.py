"""예지보전 시뮬레이터 상수 및 장비 배분 정의."""

# ====================================================================
# 시뮬레이터 타이밍 (벽시계 시간 기반 — tick 간격 드리프트 무관)
# ====================================================================
TICK_SECONDS = 15                       # 목표 샘플링 주기 (async sleep 목표)
ACCELERATION = 100                      # Path① 가속률 (실 1h = 가상 100h ≈ 4.17일)

# Path② 급성이상 이벤트 (실시간 초)
SPIKE_INTERVAL_MIN_SEC = 30 * 60        # 30분
SPIKE_INTERVAL_MAX_SEC = 90 * 60        # 90분
SPIKE_DURATION_MIN_SEC = 2 * 60         # 2분
SPIKE_DURATION_MAX_SEC = 8 * 60         # 8분

# ====================================================================
# 경로 및 고장 유형
# ====================================================================
PATH_NORMAL = "NORMAL"
PATH_NATURAL = "PATH1"   # 자연 마모
PATH_ACUTE = "PATH2"     # 급성 이상

FAULT_NORMAL = "NORMAL"
FAULT_BEARING = "BEARING_FAULT"
FAULT_MOTOR = "MOTOR_FAULT"
FAULT_COMPOUND = "COMPOUND_FAULT"
FAULT_NORMAL_ENV = "NORMAL_ENV"
FAULT_CRITICAL = "CRITICAL"
FAULT_MONITORING = "MONITORING"

# ====================================================================
# 12대 장비 배분 (DB reset_equipment_12.sql 과 동기)
#   equipment_id -> (path, planned_fault)
# ====================================================================
EQUIPMENT_PLAN = {
    # 정상 5대
    1:  (PATH_NORMAL,  FAULT_NORMAL),
    2:  (PATH_NORMAL,  FAULT_NORMAL),
    3:  (PATH_NORMAL,  FAULT_NORMAL),
    4:  (PATH_NORMAL,  FAULT_NORMAL),
    5:  (PATH_NORMAL,  FAULT_NORMAL),
    # Path ① 자연 마모 4대
    6:  (PATH_NATURAL, FAULT_BEARING),
    7:  (PATH_NATURAL, FAULT_MOTOR),
    8:  (PATH_NATURAL, FAULT_COMPOUND),
    9:  (PATH_NATURAL, FAULT_BEARING),
    # Path ② 급성 이상 3대
    10: (PATH_ACUTE,   FAULT_BEARING),
    11: (PATH_ACUTE,   FAULT_MOTOR),
    12: (PATH_ACUTE,   FAULT_COMPOUND),
}

# ====================================================================
# 정상 분포 (base, noise_sigma, diurnal_amp, load_amp)
#   — 3층 변동 구조: base + N(0,σ) + diurnal_sin + load_sin
#   — 임계값 보수적으로 두었으며 설계 검토 완료 (σ=0.06)
# ====================================================================
NORMAL_DIST = {
    "vibration":    (0.45, 0.06, 0.10, 0.05),
    "temperature":  (42.5, 2.0, 4.0,  1.0),
    "motor_current":(15.2, 0.8, 1.5,  0.5),
}

# 고장 분포 (수명 끝, health_ratio=0 일 때 기준값)
#   시나리오별로 어떤 피처가 강하게 악화되는지 모델링
FAULT_DIST = {
    FAULT_BEARING: {
        "vibration":    (6.5, 0.8, 0.2, 0.1),   # 진동 주도
        "temperature":  (60.0, 3.0, 1.0, 0.5),
        "motor_current":(28.0, 2.0, 1.0, 0.5),
    },
    FAULT_MOTOR: {
        "vibration":    (0.55, 0.10, 0.10, 0.05),  # 진동 거의 정상
        "temperature":  (85.0, 3.0, 1.0, 0.5),     # 온도 급상승
        "motor_current":(42.0, 2.0, 1.0, 0.5),     # 전류 급상승
    },
    FAULT_COMPOUND: {
        "vibration":    (2.3, 0.3, 0.2, 0.1),
        "temperature":  (78.0, 3.0, 1.0, 0.5),
        "motor_current":(43.0, 2.0, 1.0, 0.5),
    },
}

# ====================================================================
# 시뮬레이터 종료 기본값 (env 로 덮어쓰기 가능)
# ====================================================================
DEFAULT_END_TIME_ISO = None   # None=무한 실행, ISO 문자열이면 해당 시각까지

# Spring Boot 엔드포인트 경로
INGEST_PATH = "/api/sensor/ingest"
