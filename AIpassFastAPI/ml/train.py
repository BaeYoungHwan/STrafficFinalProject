"""
예지보전 모델 학습 메인 파이프라인
실행: python -m ml.train [옵션]

사용법:
  전체 학습:        python -m ml.train
  RUL만 학습:       python -m ml.train --rul-only
  분류만 학습:      python -m ml.train --cls-only
  빠른 테스트:      python -m ml.train --quick
  RandomForest:     python -m ml.train --use-rf
"""
import argparse
import shutil
import time
import sys
from datetime import datetime

from . import config
from .train_rul import train_rul_model
from .train_failure_mode import train_failure_mode_model


def main():
    parser = argparse.ArgumentParser(description="예지보전 모델 학습 파이프라인")
    parser.add_argument("--rul-only", action="store_true",
                        help="RUL 예측 모델만 학습")
    parser.add_argument("--cls-only", action="store_true",
                        help="고장모드 분류 모델만 학습")
    parser.add_argument("--use-rf", action="store_true",
                        help="고장모드 분류에 RandomForest 사용 (기본: XGBoost)")
    args = parser.parse_args()

    print("\n" + "█" * 60)
    print("  AI-Pass 예지보전 모델 학습 파이프라인")
    print("  PTZ 카메라 베어링 RUL 예측 + 고장모드 분류")
    print("█" * 60)

    total_start = time.time()
    results = {}

    # ── RUL 예측 모델 학습 ──
    if not args.cls_only:
        print("\n\n" + "─" * 60)
        print(" [1/2] RUL 예측 모델 (XGBoost Regression)")
        print("─" * 60)
        start = time.time()
        try:
            rul_result = train_rul_model()
            results["rul"] = rul_result
            elapsed = time.time() - start
            print(f"\nRUL 모델 학습 완료 ({elapsed:.1f}초)")
        except Exception as e:
            print(f"\n[ERROR] RUL 모델 학습 실패: {e}")
            import traceback
            traceback.print_exc()

    # ── 고장모드 분류 모델 학습 ──
    if not args.rul_only:
        print("\n\n" + "─" * 60)
        model_type = "RandomForest" if args.use_rf else "XGBoost"
        print(f" [2/2] 고장모드 분류 모델 ({model_type} Classification)")
        print("─" * 60)
        start = time.time()
        try:
            fm_result = train_failure_mode_model(
                use_xgboost=not args.use_rf,
            )
            results["failure_mode"] = fm_result
            elapsed = time.time() - start
            print(f"\n고장모드 분류 모델 학습 완료 ({elapsed:.1f}초)")
        except Exception as e:
            print(f"\n[ERROR] 고장모드 분류 모델 학습 실패: {e}")
            import traceback
            traceback.print_exc()

    # ── 최종 요약 ──
    total_elapsed = time.time() - total_start
    print("\n\n" + "=" * 60)
    print("  학습 결과 요약")
    print("=" * 60)

    if "rul" in results:
        r = results["rul"]
        print(f"\n  [RUL 예측]")
        print(f"    Train MAE : {r['train_mae']:.2f}일 | Train R2: {r['train_r2']:.4f}")
        print(f"    Test  MAE : {r['test_mae']:.2f}일 | Test  R2: {r['test_r2']:.4f}")
        print(f"    CV MAE    : {r['cv_mae']:.2f}일")
        print(f"    과적합 갭  : R2 {r['overfit_gap_r2']:.4f} | MAE {r['overfit_gap_mae']:.2f}일")

    if "failure_mode" in results:
        r = results["failure_mode"]
        print(f"\n  [고장모드 분류]")
        print(f"    Train Acc : {r['train_accuracy']:.4f} | Train F1: {r['train_f1']:.4f}")
        print(f"    Test  Acc : {r['test_accuracy']:.4f} | Test  F1: {r['test_f1']:.4f}")
        print(f"    ROC-AUC   : {r['roc_auc']:.4f}")
        print(f"    CV F1     : {r['cv_f1']:.4f}")
        print(f"    과적합 갭  : Acc {r['overfit_gap_acc']:.4f} | F1 {r['overfit_gap_f1']:.4f}")

    print(f"\n  총 소요 시간: {total_elapsed:.1f}초")
    print("=" * 60)

    # ── txt 리포트 저장 ──
    _save_report(results, total_elapsed)

    # ── 모델 파일 자동 백업 (타임스탬프) ──
    _backup_models()

    return results


def _save_report(results: dict, total_elapsed: float):
    """학습 결과를 txt 파일로 저장"""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    report_path = config.TRAINING_DIR / f"training_report_{timestamp}.txt"

    lines = []
    lines.append("=" * 60)
    lines.append("  AI-Pass 예지보전 모델 학습 리포트")
    lines.append(f"  생성 시각: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)

    # ── RUL 모델 리포트 ──
    if "rul" in results:
        r = results["rul"]
        lines.append("")
        lines.append("-" * 60)
        lines.append("  [1] RUL 예측 모델 (XGBoost Regression)")
        lines.append("-" * 60)
        lines.append(f"  샘플 수  : {r['n_samples']}")
        lines.append(f"  피처 수  : {r['n_features']}")
        lines.append("")
        lines.append("  -- 정확도 --")
        lines.append(f"  Train MAE  : {r['train_mae']:.2f}일")
        lines.append(f"  Train RMSE : {r['train_rmse']:.2f}일")
        lines.append(f"  Train R2   : {r['train_r2']:.4f}")
        lines.append(f"  Test  MAE  : {r['test_mae']:.2f}일")
        lines.append(f"  Test  RMSE : {r['test_rmse']:.2f}일")
        lines.append(f"  Test  R2   : {r['test_r2']:.4f}")
        lines.append(f"  CV MAE     : {r['cv_mae']:.2f}일 (+/-{r['cv_mae_std']:.2f})")
        lines.append("")
        lines.append("  -- 과적합/과소적합 분석 --")
        lines.append(f"  과적합 갭 (Train R2 - Test R2)   : {r['overfit_gap_r2']:.4f}")
        lines.append(f"  과적합 갭 (Test MAE - Train MAE) : {r['overfit_gap_mae']:.2f}일")

        if r['overfit_gap_r2'] > 0.15:
            lines.append("  판정: [과적합] Train과 Test 성능 차이가 큽니다.")
            lines.append("        -> max_depth 줄이기, reg_alpha/lambda 높이기, 데이터 증강 권장")
        elif r['train_r2'] < 0.5:
            lines.append("  판정: [과소적합] Train 성능 자체가 낮습니다.")
            lines.append("        -> n_estimators 늘리기, 피처 추가, 데이터 품질 확인 권장")
        else:
            lines.append("  판정: [양호] Train/Test 성능 균형이 좋습니다.")

        lines.append("")
        lines.append("  -- 피처 중요도 (상위 15) --")
        for name, imp in r['feature_importance'][:15]:
            lines.append(f"    {name:30s} : {imp:.4f}")

    # ── 고장모드 분류 모델 리포트 ──
    if "failure_mode" in results:
        r = results["failure_mode"]
        lines.append("")
        lines.append("-" * 60)
        lines.append("  [2] 고장모드 분류 모델 (XGBoost Classification)")
        lines.append("-" * 60)
        lines.append(f"  샘플 수  : {r['n_samples']}")
        lines.append(f"  피처 수  : {r['n_features']}")
        lines.append(f"  클래스 분포:")
        for line in r['class_distribution'].split('\n'):
            lines.append(f"    {line}")
        lines.append("")
        lines.append("  -- 정확도 --")
        lines.append(f"  Train Accuracy : {r['train_accuracy']:.4f}")
        lines.append(f"  Train F1-Score : {r['train_f1']:.4f}")
        lines.append(f"  Test  Accuracy : {r['test_accuracy']:.4f}")
        lines.append(f"  Test  F1-Score : {r['test_f1']:.4f}")
        lines.append(f"  ROC-AUC        : {r['roc_auc']:.4f}")
        lines.append(f"  CV F1-Score    : {r['cv_f1']:.4f} (+/-{r['cv_f1_std']:.4f})")
        lines.append("")
        lines.append("  -- 과적합/과소적합 분석 --")
        lines.append(f"  과적합 갭 (Train Acc - Test Acc) : {r['overfit_gap_acc']:.4f}")
        lines.append(f"  과적합 갭 (Train F1 - Test F1)   : {r['overfit_gap_f1']:.4f}")

        if r['overfit_gap_acc'] > 0.10:
            lines.append("  판정: [과적합] Train과 Test 성능 차이가 큽니다.")
            lines.append("        -> max_depth 줄이기, 데이터 증강, 정규화 강화 권장")
        elif r['train_accuracy'] < 0.7:
            lines.append("  판정: [과소적합] Train 성능 자체가 낮습니다.")
            lines.append("        -> 피처 추가, 모델 복잡도 높이기 권장")
        else:
            lines.append("  판정: [양호] Train/Test 성능 균형이 좋습니다.")

        lines.append("")
        lines.append("  -- 분류 리포트 --")
        for line in r['classification_report'].split('\n'):
            lines.append(f"  {line}")
        lines.append("")
        lines.append("  -- 혼동 행렬 --")
        for line in r['confusion_matrix'].split('\n'):
            lines.append(f"  {line}")
        lines.append("")
        lines.append("  -- 피처 중요도 (상위 15) --")
        for name, imp in r['feature_importance'][:15]:
            lines.append(f"    {name:30s} : {imp:.4f}")

    lines.append("")
    lines.append("-" * 60)
    lines.append(f"  총 소요 시간: {total_elapsed:.1f}초")
    lines.append("=" * 60)

    report_text = "\n".join(lines)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n  리포트 저장: {report_path}")


def _backup_models():
    """학습된 모델 파일을 타임스탬프 붙여서 자동 백업"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = config.MODEL_DIR / "backups"
    backup_dir.mkdir(exist_ok=True)

    # 백업 대상 파일 목록
    backup_targets = [
        config.RUL_MODEL_PATH,                          # rul_xgboost.json
        config.FAILURE_MODE_MODEL_PATH,                 # failure_mode_model.json
        config.SCALER_RUL_PATH,                         # scaler_rul.pkl
        config.SCALER_FM_PATH,                          # scaler_fm.pkl
        config.LABEL_ENCODER_PATH,                      # label_encoder.pkl
        config.MODEL_DIR / "rul_feature_cols.pkl",
        config.MODEL_DIR / "fm_feature_cols.pkl",
    ]

    backed_up = []
    for src in backup_targets:
        if src.exists():
            # rul_xgboost.json → rul_xgboost_20260312_143000.json
            stem = src.stem
            suffix = src.suffix
            dst = backup_dir / f"{stem}_{timestamp}{suffix}"
            shutil.copy2(src, dst)
            backed_up.append(dst.name)

    if backed_up:
        print(f"\n  모델 백업 완료 ({len(backed_up)}개 파일)")
        print(f"  백업 폴더: {backup_dir}")
        for name in backed_up:
            print(f"    - {name}")
    else:
        print("\n  [WARN] 백업할 모델 파일이 없습니다.")


if __name__ == "__main__":
    main()
