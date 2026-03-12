"""
예지보전 모델 학습 설정
- 데이터셋 경로, 피처 파라미터, 모델 하이퍼파라미터
"""
from pathlib import Path

# ── 데이터셋 경로 ──
DATASET_ROOT = Path(r"D:\project\데이터셋")

# Mendeley KAIST Ball Bearing (run-to-failure, 진동 + 온도)
KAIST_DIR = DATASET_ROOT / "Vibration_Bearing_RuntoFailure"

# FEMTO / PRONOSTIA (IEEE PHM 2012, run-to-failure 가속 수명 시험)
FEMTO_DIR = DATASET_ROOT / "10. FEMTO Bearing" / "FEMTOBearingDataSet"

# XJTU-SY Bearing Dataset (고장모드 라벨 존재)
XJTU_DIR = DATASET_ROOT / "XJTU-SY_Bearing_Datasets" / "Data" / "XJTU-SY_Bearing_Datasets"

# ── 모델 저장 경로 ──
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

RUL_MODEL_PATH = MODEL_DIR / "rul_xgboost.json"
FAILURE_MODE_MODEL_PATH = MODEL_DIR / "failure_mode_model.json"
SCALER_RUL_PATH = MODEL_DIR / "scaler_rul.pkl"
SCALER_FM_PATH = MODEL_DIR / "scaler_fm.pkl"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.pkl"

# ── 피처 추출 파라미터 ──
# FEMTO: 샘플링 주파수 25.6kHz, 파일당 2560 샘플 (0.1초)
FEMTO_SAMPLING_RATE = 25600
# XJTU-SY: 샘플링 주파수 25.6kHz
XJTU_SAMPLING_RATE = 25600
# KAIST: 파일당 샘플 수 다양 (1시간 간격 기록)
KAIST_SAMPLING_RATE = 25600

# ── RUL 위험도 임계값 (일 기준) ──
# FEMTO 논문 기준: vibration_rms > 20g = 고장 시점 (RUL 0)
FAILURE_THRESHOLD_RMS = 20.0  # g 단위

RUL_THRESHOLDS = {
    "LOW": 31,       # RUL >= 31일
    "MEDIUM": 16,    # 16 <= RUL <= 30일
    "HIGH": 3,       # 3 <= RUL <= 15일
    "CRITICAL": 0,   # 0 <= RUL <= 2일
}

# ── XJTU-SY 고장모드 라벨 ──
# 논문(Introduction PDF) 기반 고장모드 매핑
XJTU_FAILURE_MODES = {
    "35Hz12kN": {
        "Bearing1_1": "outer_race",
        "Bearing1_2": "outer_race",
        "Bearing1_3": "outer_race",
        "Bearing1_4": "cage",
        "Bearing1_5": "outer_race_inner_race",
    },
    "37.5Hz11kN": {
        "Bearing2_1": "inner_race",
        "Bearing2_2": "outer_race",
        "Bearing2_3": "cage",
        "Bearing2_4": "outer_race",
        "Bearing2_5": "outer_race_inner_race",
    },
    "40Hz10kN": {
        "Bearing3_1": "outer_race",
        "Bearing3_2": "inner_race_outer_race_cage",
        "Bearing3_3": "inner_race",
        "Bearing3_4": "inner_race",
        "Bearing3_5": "outer_race",
    },
}

# PTZ 카메라 고장모드로 매핑 (프로젝트 도메인 적용)
# 베어링 고장모드 → PTZ 카메라 고장모드 매핑
FAILURE_MODE_MAPPING = {
    "outer_race": "bearing_wear",          # 베어링 마모
    "inner_race": "motor_overheat",        # 모터 과열
    "cage": "bearing_wear",                # 베어링 마모 (케이지)
    "outer_race_inner_race": "bearing_wear",
    "inner_race_outer_race_cage": "motor_overheat",
}

# ── XGBoost 하이퍼파라미터 ──
XGBOOST_RUL_PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
}

XGBOOST_CLASSIFIER_PARAMS = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
}

RANDOM_FOREST_PARAMS = {
    "n_estimators": 200,
    "max_depth": 10,
    "min_samples_split": 5,
    "min_samples_leaf": 2,
    "random_state": 42,
    "n_jobs": -1,
}
