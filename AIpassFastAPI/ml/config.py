"""
예지보전 모델 학습 설정
- 데이터셋 경로, 9개 센서 피처, 모델 하이퍼파라미터
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

# ── 전처리 CSV 저장 경로 ──
PREPROCESSED_DIR = DATASET_ROOT / "preprocessed"
RUL_CSV_V2_PATH = PREPROCESSED_DIR / "rul_dataset_9feat.csv"
FM_CSV_V2_PATH = PREPROCESSED_DIR / "failure_mode_dataset_9feat.csv"

# ── 모델 저장 경로 ──
MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

# ── 결과 저장 폴더 ──
TRAINING_DIR = MODEL_DIR / "training"
TRAINING_DIR.mkdir(exist_ok=True)
VALIDATION_DIR = MODEL_DIR / "validation"
VALIDATION_DIR.mkdir(exist_ok=True)
VALIDATION_CSV_DIR = MODEL_DIR / "validation_csv"
VALIDATION_CSV_DIR.mkdir(exist_ok=True)

RUL_MODEL_PATH = MODEL_DIR / "rul_xgboost.json"
FAILURE_MODE_MODEL_PATH = MODEL_DIR / "failure_mode_model.json"
SCALER_RUL_PATH = MODEL_DIR / "scaler_rul.pkl"
SCALER_FM_PATH = MODEL_DIR / "scaler_fm.pkl"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.pkl"

# ── 9개 센서 피처 (DB 스키마 일치) ──
# 학습/운영 모두 동일한 9개 피처 사용
FEATURE_COLUMNS_9 = [
    "vibration_rms",     # 진동 RMS (g)
    "temperature",       # 기기 온도 (°C)
    "temp_residual",     # 온도 잔차 = 기기온도 - ExpectedTemp
    "motor_current",     # 모터 전류 (A) - 학습 시 더미
    "operating_hours",   # 누적 가동 시간 (h)
    "ambient_temp",      # 외기 온도 (°C) - 기상청 API
    "wind_speed",        # 풍속 (m/s) - 기상청 API
    "humidity",          # 습도 (%) - 기상청 API
    "season",            # 계절 (0=봄, 1=여름, 2=가을, 3=겨울)
]

# 환경 보정 공식 파라미터
# ExpectedTemp = ambient_temp + AVG_HEAT_GENERATION
# temp_residual = temperature - ExpectedTemp
AVG_HEAT_GENERATION = 35.0  # 장비 평균 발열값 (°C) - 학습 데이터에서 산출 후 갱신

# ── 샘플링 레이트 (전처리에서 RMS 계산 시 사용) ──
KAIST_SAMPLING_RATE = 25600
FEMTO_SAMPLING_RATE = 25600
XJTU_SAMPLING_RATE = 25600

# ── RUL 위험도 임계값 (일 기준) ──
FAILURE_THRESHOLD_RMS = 20.0  # g 단위

RUL_THRESHOLDS = {
    "LOW": 31,       # RUL >= 31일
    "MEDIUM": 16,    # 16 <= RUL <= 30일
    "HIGH": 3,       # 3 <= RUL <= 15일
    "CRITICAL": 0,   # 0 <= RUL <= 2일
}

# ── XJTU-SY 고장모드 라벨 ──
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

# PTZ 카메라 고장모드로 매핑
FAILURE_MODE_MAPPING = {
    "outer_race": "bearing_wear",
    "inner_race": "motor_overheat",
    "cage": "bearing_wear",
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

# ── 기상청 API 관측소 ──
WEATHER_STN_ID = "112"  # 인천 (강화도 인근)
