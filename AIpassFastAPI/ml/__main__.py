"""
python -m ml.preprocess_9feat  → 9피처 전처리 CSV 생성 (1단계)
python -m ml.train             → 모델 학습 (2단계)
python -m ml.validate          → 테스트셋 검증 (3단계)
"""
from .train import main

if __name__ == "__main__":
    main()
