"""
9피처 전처리 CSV 테스트셋 기반 모델 검증
실행: python -X utf8 -m ml.validate

학습 시와 동일한 분할(random_state=42, test_size=0.2)로
테스트셋을 재현하여 저장된 모델로 독립 검증
"""
import time
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, f1_score, roc_auc_score,
    classification_report, confusion_matrix
)
from xgboost import XGBRegressor, XGBClassifier

from . import config


def _rul_to_risk(rul_days: float) -> str:
    """RUL 값 → 위험도 등급"""
    if rul_days >= config.RUL_THRESHOLDS["LOW"]:
        return "LOW"
    elif rul_days >= config.RUL_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    elif rul_days >= config.RUL_THRESHOLDS["HIGH"]:
        return "HIGH"
    else:
        return "CRITICAL"


def validate():
    print("\n" + "=" * 60)
    print("  AI-Pass 모델 검증 (테스트셋 기반, 9피처)")
    print("=" * 60)
    start_time = time.time()

    rul_metrics = None
    fm_metrics = None
    df_rul_detail = None
    df_fm_detail = None

    # ══════════════════════════════════════════════════════
    # [1] RUL 예측 모델 검증
    # ══════════════════════════════════════════════════════
    print("\n" + "-" * 60)
    print("  [1/2] RUL 예측 모델 검증")
    print("-" * 60)

    if not config.RUL_CSV_V2_PATH.exists():
        print("  [SKIP] 전처리 CSV 없음. python -m ml.preprocess_9feat 먼저 실행하세요.")
    else:
        # 데이터 로딩
        print(f"  CSV 로딩: {config.RUL_CSV_V2_PATH}")
        df = pd.read_csv(config.RUL_CSV_V2_PATH, low_memory=False)
        feature_cols = [c for c in config.FEATURE_COLUMNS_9 if c in df.columns]
        X = df[feature_cols].copy()
        y = df["rul_days"].copy()
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

        # 학습 시와 동일한 분할
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        print(f"  테스트셋: {len(X_test)}개 샘플 (전체 {len(X)}의 20%)")

        # 모델 로딩
        rul_model = XGBRegressor()
        rul_model.load_model(str(config.RUL_MODEL_PATH))
        rul_scaler = joblib.load(config.SCALER_RUL_PATH)

        # 추론
        X_test_scaled = rul_scaler.transform(X_test)
        y_pred = np.maximum(rul_model.predict(X_test_scaled), 0)

        # 지표 계산
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        # 위험도 등급 비교
        actual_risks = [_rul_to_risk(v) for v in y_test]
        pred_risks = [_rul_to_risk(v) for v in y_pred]
        risk_match = sum(a == p for a, p in zip(actual_risks, pred_risks))
        risk_accuracy = risk_match / len(y_test)

        rul_metrics = {
            "n_test": len(X_test),
            "n_total": len(X),
            "n_features": len(feature_cols),
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "risk_accuracy": risk_accuracy,
        }

        # 구간별 분석
        rul_metrics["by_risk"] = {}
        df_test = pd.DataFrame({
            "actual_rul": y_test.values,
            "predicted_rul": np.round(y_pred, 1),
            "error": np.abs(y_test.values - y_pred),
            "actual_risk": actual_risks,
            "predicted_risk": pred_risks,
            "risk_match": [a == p for a, p in zip(actual_risks, pred_risks)],
        }, index=X_test.index)

        for risk in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            subset = df_test[df_test["actual_risk"] == risk]
            if len(subset) > 0:
                rul_metrics["by_risk"][risk] = {
                    "count": len(subset),
                    "mae": round(subset["error"].mean(), 2),
                    "risk_accuracy": round(subset["risk_match"].mean(), 4),
                }

        # 오차 큰 상위 10
        df_test_sorted = df_test.nlargest(10, "error")
        rul_metrics["worst"] = df_test_sorted[
            ["actual_rul", "predicted_rul", "error", "actual_risk", "predicted_risk"]
        ].to_dict("records")

        # 상세 CSV용
        df_rul_detail = df_test.reset_index(drop=True)

        # 콘솔 출력
        print(f"\n  MAE  : {mae:.2f}일")
        print(f"  RMSE : {rmse:.2f}일")
        print(f"  R2   : {r2:.4f}")
        print(f"  위험도 등급 일치율: {risk_accuracy*100:.1f}%")
        print(f"\n  구간별:")
        for risk in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if risk in rul_metrics["by_risk"]:
                r = rul_metrics["by_risk"][risk]
                print(f"    {risk:10s}: MAE {r['mae']:6.2f}일 | "
                      f"등급일치 {r['risk_accuracy']*100:.1f}% | "
                      f"샘플 {r['count']}개")

    # ══════════════════════════════════════════════════════
    # [2] 고장모드 분류 모델 검증
    # ══════════════════════════════════════════════════════
    print("\n" + "-" * 60)
    print("  [2/2] 고장모드 분류 모델 검증")
    print("-" * 60)

    if not config.FM_CSV_V2_PATH.exists():
        print("  [SKIP] 전처리 CSV 없음. python -m ml.preprocess_9feat 먼저 실행하세요.")
    else:
        # 데이터 로딩
        print(f"  CSV 로딩: {config.FM_CSV_V2_PATH}")
        df = pd.read_csv(config.FM_CSV_V2_PATH, low_memory=False)
        feature_cols = [c for c in config.FEATURE_COLUMNS_9 if c in df.columns]
        X = df[feature_cols].copy()
        y_raw = df["failure_mode"].copy()
        X = X.replace([np.inf, -np.inf], np.nan).fillna(0)

        # 라벨 인코딩 (학습 시와 동일하게 재현)
        label_encoder = LabelEncoder()
        y = label_encoder.fit_transform(y_raw)

        # 학습 시와 동일한 분할
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"  테스트셋: {len(X_test)}개 샘플 (전체 {len(X)}의 20%)")

        # 모델 로딩
        fm_model = XGBClassifier()
        fm_model.load_model(str(config.FAILURE_MODE_MODEL_PATH))
        fm_scaler = joblib.load(config.SCALER_FM_PATH)
        fm_label_encoder = joblib.load(config.LABEL_ENCODER_PATH)

        # 추론
        X_test_scaled = fm_scaler.transform(X_test)
        y_pred = fm_model.predict(X_test_scaled)
        y_pred_proba = fm_model.predict_proba(X_test_scaled)

        # 지표 계산
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")

        n_classes = len(fm_label_encoder.classes_)
        if n_classes == 2:
            roc_auc = roc_auc_score(y_test, y_pred_proba[:, 1])
        else:
            roc_auc = roc_auc_score(y_test, y_pred_proba,
                                     multi_class="ovr", average="weighted")

        target_names = list(fm_label_encoder.classes_)
        cls_report = classification_report(y_test, y_pred,
                                            target_names=target_names)
        cm = confusion_matrix(y_test, y_pred)

        fm_metrics = {
            "n_test": len(X_test),
            "n_total": len(X),
            "n_features": len(feature_cols),
            "accuracy": accuracy,
            "f1": f1,
            "roc_auc": roc_auc,
            "classification_report": cls_report,
            "confusion_matrix": pd.DataFrame(
                cm, index=target_names, columns=target_names
            ).to_string(),
            "classes": target_names,
        }

        # 상세 CSV용
        actual_modes = fm_label_encoder.inverse_transform(y_test)
        pred_modes = fm_label_encoder.inverse_transform(y_pred)
        confidence = np.max(y_pred_proba, axis=1)

        fm_detail_data = {
            "actual_mode": actual_modes,
            "predicted_mode": pred_modes,
            "correct": actual_modes == pred_modes,
            "confidence": np.round(confidence, 4),
        }
        for i, cls_name in enumerate(fm_label_encoder.classes_):
            fm_detail_data[f"prob_{cls_name}"] = np.round(y_pred_proba[:, i], 4)

        df_fm_detail = pd.DataFrame(fm_detail_data)

        # 콘솔 출력
        print(f"\n  Accuracy : {accuracy:.4f} ({accuracy*100:.1f}%)")
        print(f"  F1-Score : {f1:.4f}")
        print(f"  ROC-AUC  : {roc_auc:.4f}")
        print(f"\n  분류 리포트:")
        for line in cls_report.split("\n"):
            print(f"    {line}")
        print(f"\n  혼동 행렬:")
        cm_df = pd.DataFrame(cm, index=target_names, columns=target_names)
        for line in cm_df.to_string().split("\n"):
            print(f"    {line}")

    # ══════════════════════════════════════════════════════
    # 결과 저장
    # ══════════════════════════════════════════════════════
    elapsed = time.time() - start_time

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    # CSV 저장
    if df_rul_detail is not None:
        csv_path = config.VALIDATION_CSV_DIR / f"validation_rul_detail_{timestamp}.csv"
        df_rul_detail.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"\n  CSV (RUL)  : {csv_path}")

    if df_fm_detail is not None:
        csv_path = config.VALIDATION_CSV_DIR / f"validation_fm_detail_{timestamp}.csv"
        df_fm_detail.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  CSV (FM)   : {csv_path}")

    # TXT 리포트 저장
    txt_path = config.VALIDATION_DIR / f"validation_report_{timestamp}.txt"
    lines = _build_report(rul_metrics, fm_metrics, elapsed, now)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  TXT (리포트): {txt_path}")

    # 최종 요약
    print("\n" + "=" * 60)
    print("  검증 결과 요약")
    print("=" * 60)
    if rul_metrics:
        print(f"  [RUL] MAE: {rul_metrics['mae']:.2f}일 | "
              f"R2: {rul_metrics['r2']:.4f} | "
              f"등급일치: {rul_metrics['risk_accuracy']*100:.1f}%")
    if fm_metrics:
        print(f"  [FM]  Acc: {fm_metrics['accuracy']*100:.1f}% | "
              f"F1: {fm_metrics['f1']:.4f} | "
              f"AUC: {fm_metrics['roc_auc']:.4f}")
    print(f"  소요 시간: {elapsed:.1f}초")
    print("=" * 60)

    return {"rul": rul_metrics, "fm": fm_metrics}


def _build_report(rul_metrics, fm_metrics, elapsed, now) -> list:
    """TXT 리포트 생성"""
    lines = []
    lines.append("=" * 60)
    lines.append("  AI-Pass 모델 검증 리포트 (테스트셋 기반, 9피처)")
    lines.append(f"  검증 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"  검증 방법: 학습 시 분리된 20% 테스트셋 (random_state=42)")
    lines.append("=" * 60)

    # ── RUL ──
    if rul_metrics:
        lines.append("")
        lines.append("-" * 60)
        lines.append("  [1] RUL 예측 모델 검증")
        lines.append("-" * 60)
        lines.append(f"  전체 샘플: {rul_metrics['n_total']} | "
                     f"테스트 샘플: {rul_metrics['n_test']} | "
                     f"피처: {rul_metrics['n_features']}개")
        lines.append("")
        lines.append(f"  MAE  : {rul_metrics['mae']:.2f}일")
        lines.append(f"  RMSE : {rul_metrics['rmse']:.2f}일")
        lines.append(f"  R2   : {rul_metrics['r2']:.4f}")
        lines.append(f"  위험도 등급 일치율: {rul_metrics['risk_accuracy']:.4f} "
                     f"({rul_metrics['risk_accuracy']*100:.1f}%)")

        lines.append("")
        lines.append("  -- 위험도 구간별 분석 --")
        for risk in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if risk in rul_metrics["by_risk"]:
                r = rul_metrics["by_risk"][risk]
                lines.append(f"    {risk:10s}: MAE {r['mae']:6.2f}일 | "
                             f"등급일치 {r['risk_accuracy']:.4f} | "
                             f"샘플 {r['count']}개")

        lines.append("")
        lines.append("  -- 오차 큰 샘플 상위 10 --")
        for w in rul_metrics["worst"]:
            lines.append(f"    실제 {w['actual_rul']:.1f}일({w['actual_risk']}) -> "
                         f"예측 {w['predicted_rul']:.1f}일({w['predicted_risk']}) | "
                         f"오차 {w['error']:.1f}일")

        # 판정
        lines.append("")
        if rul_metrics["r2"] >= 0.8:
            lines.append("  판정: [양호] R2 0.8 이상, 예측 정확도 우수")
        elif rul_metrics["r2"] >= 0.6:
            lines.append("  판정: [보통] R2 0.6~0.8, 개선 여지 있음")
        else:
            lines.append("  판정: [미흡] R2 0.6 미만, 모델 개선 필요")

    # ── 고장모드 ──
    if fm_metrics:
        lines.append("")
        lines.append("-" * 60)
        lines.append("  [2] 고장모드 분류 모델 검증")
        lines.append("-" * 60)
        lines.append(f"  전체 샘플: {fm_metrics['n_total']} | "
                     f"테스트 샘플: {fm_metrics['n_test']} | "
                     f"피처: {fm_metrics['n_features']}개")
        lines.append("")
        lines.append(f"  Accuracy : {fm_metrics['accuracy']:.4f} ({fm_metrics['accuracy']*100:.1f}%)")
        lines.append(f"  F1-Score : {fm_metrics['f1']:.4f}")
        lines.append(f"  ROC-AUC  : {fm_metrics['roc_auc']:.4f}")

        lines.append("")
        lines.append("  -- 분류 리포트 --")
        for line in fm_metrics["classification_report"].split("\n"):
            lines.append(f"    {line}")

        lines.append("")
        lines.append("  -- 혼동 행렬 --")
        for line in fm_metrics["confusion_matrix"].split("\n"):
            lines.append(f"    {line}")

        # 판정
        lines.append("")
        if fm_metrics["accuracy"] >= 0.85:
            lines.append("  판정: [양호] 정확도 85% 이상")
        elif fm_metrics["accuracy"] >= 0.7:
            lines.append("  판정: [보통] 정확도 70~85%")
        else:
            lines.append("  판정: [미흡] 정확도 70% 미만")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"  총 소요 시간: {elapsed:.1f}초")
    lines.append("=" * 60)

    return lines


if __name__ == "__main__":
    validate()
