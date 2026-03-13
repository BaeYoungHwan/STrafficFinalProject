"""
고장모드 분류 모델 학습 - XGBoost / RandomForest Classification
- 9개 센서 피처 기반 (DB 스키마 일치)
- XJTU-SY 데이터셋 기반
- PTZ 카메라 고장모드: bearing_wear(베어링 마모) / motor_overheat(모터 과열)
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix
)
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from . import config


def train_failure_mode_model(use_xgboost: bool = True) -> dict:
    """
    고장모드 분류 모델 학습 (전처리된 9피처 CSV 기반)

    Args:
        use_xgboost: True=XGBoost, False=RandomForest

    Returns:
        dict: 학습 결과 (metrics, model, scaler, encoder)
    """
    model_name = "XGBoost" if use_xgboost else "RandomForest"
    print("=" * 60)
    print(f"고장모드 분류 모델 ({model_name} Classification) 학습 시작")
    print("=" * 60)

    # ── 1. 데이터 로딩 ──
    if config.FM_CSV_V2_PATH.exists():
        print(f"\n9피처 전처리 CSV 로딩: {config.FM_CSV_V2_PATH}")
        df = pd.read_csv(config.FM_CSV_V2_PATH)
        print(f"  {len(df)}개 샘플 로딩 완료 (9피처)")
    else:
        raise FileNotFoundError(
            f"전처리 CSV가 없습니다: {config.FM_CSV_V2_PATH}\n"
            f"  → python -m ml.preprocess_9feat 먼저 실행하세요."
        )

    if df.empty:
        raise ValueError("고장모드 분류 학습 데이터를 불러올 수 없습니다.")

    # ── 2. 피처/타겟 분리 ──
    feature_cols = [c for c in config.FEATURE_COLUMNS_9 if c in df.columns]
    X = df[feature_cols].copy()
    y_raw = df["failure_mode"].copy()

    # 라벨 인코딩
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    # NaN/Inf 처리
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)

    print(f"\n피처 수: {len(feature_cols)}")
    print(f"샘플 수: {len(X)}")
    print(f"클래스: {list(label_encoder.classes_)}")
    print(f"클래스 분포:\n{pd.Series(y_raw).value_counts().to_string()}")

    # ── 3. 학습/테스트 분할 ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ── 4. 스케일링 ──
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ── 5. 모델 학습 ──
    if use_xgboost:
        n_classes = len(label_encoder.classes_)
        params = config.XGBOOST_CLASSIFIER_PARAMS.copy()
        if n_classes == 2:
            params["objective"] = "binary:logistic"
            params["eval_metric"] = "logloss"
        else:
            params["objective"] = "multi:softprob"
            params["eval_metric"] = "mlogloss"
        model = XGBClassifier(**params)
    else:
        model = RandomForestClassifier(**config.RANDOM_FOREST_PARAMS)

    print(f"\n{model_name} 모델 학습 중...")
    if use_xgboost:
        model.fit(
            X_train_scaled, y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=50,
        )
    else:
        model.fit(X_train_scaled, y_train)

    # ── 6. 예측 및 평가 (Train + Test 비교 → 과적합/과소적합 분석) ──
    # Train 성능
    y_pred_train = model.predict(X_train_scaled)
    train_accuracy = accuracy_score(y_train, y_pred_train)
    train_f1 = f1_score(y_train, y_pred_train, average="weighted")

    # Test 성능
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="weighted")

    # ROC-AUC
    n_classes = len(label_encoder.classes_)
    if n_classes == 2:
        roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
    else:
        roc_auc = roc_auc_score(
            y_test, y_pred_proba, multi_class="ovr", average="weighted"
        )

    # 과적합/과소적합 분석
    overfit_gap_acc = train_accuracy - accuracy
    overfit_gap_f1 = train_f1 - f1

    print("\n" + "=" * 40)
    print("고장모드 분류 모델 평가 결과")
    print("=" * 40)
    print(f"[Train] Accuracy: {train_accuracy:.4f} | F1: {train_f1:.4f}")
    print(f"[Test]  Accuracy: {accuracy:.4f} | F1: {f1:.4f} | ROC-AUC: {roc_auc:.4f}")
    print(f"\n과적합 갭 (Train Acc - Test Acc): {overfit_gap_acc:.4f}")
    print(f"과적합 갭 (Train F1 - Test F1):   {overfit_gap_f1:.4f}")
    if overfit_gap_acc > 0.10:
        print("  >> 과적합 경향 감지: Train과 Test 성능 차이가 큽니다.")
    elif train_accuracy < 0.7:
        print("  >> 과소적합 경향 감지: Train 성능 자체가 낮습니다.")
    else:
        print("  >> 적합도 양호: Train/Test 성능 균형이 좋습니다.")

    # 분류 리포트
    target_names = list(label_encoder.classes_)
    print("\n분류 리포트:")
    print(classification_report(y_test, y_pred, target_names=target_names))

    # 혼동 행렬
    cm = confusion_matrix(y_test, y_pred)
    print("혼동 행렬:")
    print(pd.DataFrame(cm, index=target_names, columns=target_names))

    # ── 7. 교차 검증 ──
    print("\n5-Fold 교차 검증 중...")
    X_all_scaled = scaler.transform(X)
    if use_xgboost:
        cv_model = XGBClassifier(**config.XGBOOST_CLASSIFIER_PARAMS)
    else:
        cv_model = RandomForestClassifier(**config.RANDOM_FOREST_PARAMS)
    cv_scores = cross_val_score(cv_model, X_all_scaled, y, cv=5, scoring="f1_weighted")
    cv_f1 = cv_scores.mean()
    print(f"CV F1-Score: {cv_f1:.4f} (±{cv_scores.std():.4f})")

    # ── 8. 피처 중요도 ──
    importance = model.feature_importances_
    feat_importance = sorted(
        zip(feature_cols, importance), key=lambda x: x[1], reverse=True
    )
    print("\n피처 중요도:")
    for name, imp in feat_importance:
        print(f"  {name:20s} : {imp:.4f}")

    # ── 9. 모델 저장 ──
    if use_xgboost:
        model.save_model(str(config.FAILURE_MODE_MODEL_PATH))
    else:
        joblib.dump(model, config.FAILURE_MODE_MODEL_PATH)

    joblib.dump(scaler, config.SCALER_FM_PATH)
    joblib.dump(label_encoder, config.LABEL_ENCODER_PATH)
    joblib.dump(feature_cols, config.MODEL_DIR / "fm_feature_cols.pkl")

    print(f"\n모델 저장 완료:")
    print(f"  모델      : {config.FAILURE_MODE_MODEL_PATH}")
    print(f"  스케일러  : {config.SCALER_FM_PATH}")
    print(f"  라벨인코더: {config.LABEL_ENCODER_PATH}")

    # 분류 리포트 문자열 저장용
    cls_report_str = classification_report(y_test, y_pred, target_names=target_names)
    cm_str = pd.DataFrame(cm, index=target_names, columns=target_names).to_string()

    return {
        "train_accuracy": train_accuracy,
        "train_f1": train_f1,
        "test_accuracy": accuracy,
        "test_f1": f1,
        "roc_auc": roc_auc,
        "overfit_gap_acc": overfit_gap_acc,
        "overfit_gap_f1": overfit_gap_f1,
        "cv_f1": cv_f1,
        "cv_f1_std": cv_scores.std(),
        "n_samples": len(X),
        "n_features": len(feature_cols),
        "class_distribution": pd.Series(y_raw).value_counts().to_string(),
        "classification_report": cls_report_str,
        "confusion_matrix": cm_str,
        "feature_importance": feat_importance,
        "model": model,
        "scaler": scaler,
        "label_encoder": label_encoder,
        "feature_cols": feature_cols,
    }


def predict_failure_mode(features: dict, model=None, scaler=None,
                         label_encoder=None, feature_cols=None,
                         use_xgboost: bool = True) -> dict:
    """
    단일 샘플에 대한 고장모드 분류 (추론용)

    Args:
        features: 9개 센서 피처 딕셔너리

    Returns:
        dict: failure_mode, confidence, probabilities
    """
    if model is None:
        if use_xgboost:
            model = XGBClassifier()
            model.load_model(str(config.FAILURE_MODE_MODEL_PATH))
        else:
            model = joblib.load(config.FAILURE_MODE_MODEL_PATH)
    if scaler is None:
        scaler = joblib.load(config.SCALER_FM_PATH)
    if label_encoder is None:
        label_encoder = joblib.load(config.LABEL_ENCODER_PATH)
    if feature_cols is None:
        feature_cols = joblib.load(config.MODEL_DIR / "fm_feature_cols.pkl")

    # 피처 벡터 생성
    x = np.array([[features.get(col, 0) for col in feature_cols]])
    x = np.nan_to_num(x, nan=0, posinf=0, neginf=0)
    x_scaled = scaler.transform(x)

    pred = model.predict(x_scaled)[0]
    proba = model.predict_proba(x_scaled)[0]

    failure_mode = label_encoder.inverse_transform([pred])[0]
    confidence = float(max(proba))

    probabilities = {
        label_encoder.inverse_transform([i])[0]: float(p)
        for i, p in enumerate(proba)
    }

    return {
        "failure_mode": failure_mode,
        "confidence": round(confidence, 4),
        "probabilities": probabilities,
    }
