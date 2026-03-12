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
import time
import sys

from .train_rul import train_rul_model
from .train_failure_mode import train_failure_mode_model


def main():
    parser = argparse.ArgumentParser(description="예지보전 모델 학습 파이프라인")
    parser.add_argument("--rul-only", action="store_true",
                        help="RUL 예측 모델만 학습")
    parser.add_argument("--cls-only", action="store_true",
                        help="고장모드 분류 모델만 학습")
    parser.add_argument("--quick", action="store_true",
                        help="빠른 테스트 (데이터 일부만 사용)")
    parser.add_argument("--use-rf", action="store_true",
                        help="고장모드 분류에 RandomForest 사용 (기본: XGBoost)")
    parser.add_argument("--max-kaist", type=int, default=None,
                        help="KAIST 데이터 최대 파일 수")
    parser.add_argument("--max-femto", type=int, default=None,
                        help="FEMTO 베어링당 최대 파일 수")
    parser.add_argument("--max-xjtu", type=int, default=None,
                        help="XJTU-SY 베어링당 최대 파일 수")
    args = parser.parse_args()

    # 빠른 테스트 모드
    if args.quick:
        args.max_kaist = args.max_kaist or 30
        args.max_femto = args.max_femto or 100
        args.max_xjtu = args.max_xjtu or 50
        print("[Quick] 모드: 데이터 일부만 사용하여 빠른 검증")

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
            rul_result = train_rul_model(
                max_kaist=args.max_kaist,
                max_femto_per_bearing=args.max_femto,
            )
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
                max_files_per_bearing=args.max_xjtu,
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
    print("\n\n" + "█" * 60)
    print("  학습 결과 요약")
    print("█" * 60)

    if "rul" in results:
        r = results["rul"]
        print(f"\n  [RUL 예측]")
        print(f"    MAE     : {r['mae']:.2f}일")
        print(f"    RMSE    : {r['rmse']:.2f}일")
        print(f"    R²      : {r['r2']:.4f}")
        print(f"    CV MAE  : {r['cv_mae']:.2f}일")

    if "failure_mode" in results:
        r = results["failure_mode"]
        print(f"\n  [고장모드 분류]")
        print(f"    Accuracy : {r['accuracy']:.4f}")
        print(f"    F1-Score : {r['f1_score']:.4f}")
        print(f"    ROC-AUC  : {r['roc_auc']:.4f}")
        print(f"    CV F1    : {r['cv_f1']:.4f}")

    print(f"\n  총 소요 시간: {total_elapsed:.1f}초")
    print("█" * 60)

    return results


if __name__ == "__main__":
    main()
