"""
RUL(잔여수명) 예측 모델 학습 - XGBoost Regression
- KAIST + FEMTO 데이터셋 통합 학습
- 환경 보정 피처 포함
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score
)
from xgboost import XGBRegressor

from . import config
from .data_loader import load_rul_dataset, get_feature_columns


def train_rul_model(max_kaist: int = None,
                    max_femto_per_bearing: int = None) -> dict:
    """
    RUL 예측 모델 학습

    Args:
        max_kaist: KAIST 최대 파일 수 (None=전체)
        max_femto_per_bearing: FEMTO 베어링당 최대 파일 수

    Returns:
        dict: 학습 결과 (metrics, model, scaler)
    """
    # ── 1. 데이터 로딩 ──
    print("=" * 60)
    print("RUL 예측 모델 (XGBoost Regression) 학습 시작")
    print("=" * 60)

    df = load_rul_dataset(
        max_kaist=max_kaist,
        max_femto_per_bearing=max_femto_per_bearing,
    )

    # ── 2. 피처/타겟 분리 ──
    feature_cols = get_feature_columns(df)
    X = df[feature_cols].copy()
    y = df["rul_days"].copy()

    # NaN/Inf 처리
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    print(f"\n피처 수: {len(feature_cols)}")
    print(f"샘플 수: {len(X)}")
    print(f"RUL 범위: {y.min():.1f} ~ {y.max():.1f}일")

    # ── 3. 학습/테스트 분할 ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ── 4. 스케일링 ──
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── 5. 모델 학습 ──
    model = XGBRegressor(**config.XGBOOST_RUL_PARAMS)

    print("\n모델 학습 중...")
    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=50,
    )

    # ── 6. 예측 및 평가 ──
    y_pred = model.predict(X_test_scaled)
    # RUL은 음수가 될 수 없음
    y_pred = np.maximum(y_pred, 0)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print("\n" + "=" * 40)
    print("RUL 모델 평가 결과")
    print("=" * 40)
    print(f"MAE  : {mae:.2f}일")
    print(f"RMSE : {rmse:.2f}일")
    print(f"R²   : {r2:.4f}")

    # ── 7. 교차 검증 ──
    print("\n5-Fold 교차 검증 중...")
    X_all_scaled = scaler.transform(X)
    cv_scores = cross_val_score(
        XGBRegressor(**config.XGBOOST_RUL_PARAMS),
        X_all_scaled, y, cv=5, scoring="neg_mean_absolute_error"
    )
    cv_mae = -cv_scores.mean()
    print(f"CV MAE: {cv_mae:.2f}일 (±{cv_scores.std():.2f})")

    # ── 8. 피처 중요도 ──
    importance = model.feature_importances_
    feat_importance = sorted(
        zip(feature_cols, importance), key=lambda x: x[1], reverse=True
    )
    print("\n상위 10 피처 중요도:")
    for name, imp in feat_importance[:10]:
        print(f"  {name:30s} : {imp:.4f}")

    # ── 9. 모델 저장 ──
    model.save_model(str(config.RUL_MODEL_PATH))
    joblib.dump(scaler, config.SCALER_RUL_PATH)

    # 피처 컬럼 순서 저장 (추론 시 필요)
    joblib.dump(feature_cols, config.MODEL_DIR / "rul_feature_cols.pkl")

    print(f"\n모델 저장 완료:")
    print(f"  모델  : {config.RUL_MODEL_PATH}")
    print(f"  스케일러: {config.SCALER_RUL_PATH}")

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "cv_mae": cv_mae,
        "feature_importance": feat_importance,
        "model": model,
        "scaler": scaler,
        "feature_cols": feature_cols,
    }


def predict_rul(features: dict, model=None, scaler=None,
                feature_cols=None) -> dict:
    """
    단일 샘플에 대한 RUL 예측 (추론용)

    Args:
        features: extract_features()로 추출된 피처 딕셔너리
        model: 학습된 XGBRegressor (None이면 파일에서 로딩)
        scaler: StandardScaler (None이면 파일에서 로딩)
        feature_cols: 피처 컬럼 리스트

    Returns:
        dict: rul_days, risk_level
    """
    if model is None:
        model = XGBRegressor()
        model.load_model(str(config.RUL_MODEL_PATH))
    if scaler is None:
        scaler = joblib.load(config.SCALER_RUL_PATH)
    if feature_cols is None:
        feature_cols = joblib.load(config.MODEL_DIR / "rul_feature_cols.pkl")

    # 피처 벡터 생성
    x = np.array([[features.get(col, 0) for col in feature_cols]])
    x = np.nan_to_num(x, nan=0, posinf=0, neginf=0)
    x_scaled = scaler.transform(x)

    rul_days = float(max(0, model.predict(x_scaled)[0]))

    # 위험도 등급 판정
    if rul_days >= config.RUL_THRESHOLDS["LOW"]:
        risk_level = "LOW"
    elif rul_days >= config.RUL_THRESHOLDS["MEDIUM"]:
        risk_level = "MEDIUM"
    elif rul_days >= config.RUL_THRESHOLDS["HIGH"]:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    return {
        "rul_days": round(rul_days, 1),
        "risk_level": risk_level,
    }
