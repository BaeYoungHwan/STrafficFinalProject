"""
YOLO 번호판 감지 모델 fine-tuning.
실행: cd AIpassFastAPI && python scripts/train_plate_detector.py
학습 완료 후 best.pt → services/plate_yolo.pt 자동 복사
"""
import shutil
import logging
import yaml
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).resolve().parent.parent   # AIpassFastAPI/
DATA_YAML    = ROOT / "data" / "plate_dataset" / "data.yaml"
OUTPUT_MODEL = ROOT / "services" / "plate_yolo.pt"
RUNS_DIR     = ROOT / "runs" / "detect"


def _find_best_pt() -> Path:
    """runs/detect/plate_yolo*/weights/best.pt 중 mtime 최신 선택."""
    candidates = list(RUNS_DIR.glob("plate_yolo*/weights/best.pt"))
    if not candidates:
        raise FileNotFoundError(f"best.pt를 찾을 수 없습니다: {RUNS_DIR}/plate_yolo*/weights/best.pt")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _patch_data_yaml_path(yaml_path: Path) -> Path:
    """
    YOLO는 data.yaml의 path: 를 cwd 기준으로 해석한다.
    path를 절대경로로 패치한 임시 yaml을 같은 디렉터리에 생성해 반환.
    """
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    dataset_dir = yaml_path.parent.resolve()
    data['path'] = str(dataset_dir)

    patched_path = yaml_path.parent / "data_abs.yaml"
    with open(patched_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    logger.info("data.yaml 절대경로 패치: path=%s → %s", dataset_dir, patched_path)
    return patched_path


def main():
    if not DATA_YAML.exists():
        logger.error("data.yaml 없음 — generate_annotations.py 먼저 실행하세요: %s", DATA_YAML)
        return

    logger.info("data.yaml: %s", DATA_YAML)
    logger.info("출력 모델: %s", OUTPUT_MODEL)

    # YOLO path 해석 문제 해결: 절대경로 패치
    patched_yaml = _patch_data_yaml_path(DATA_YAML)

    from ultralytics import YOLO

    model = YOLO("yolo26n.pt")
    logger.info("yolo26n.pt 로드 완료 — 학습 시작")

    model.train(
        data=str(patched_yaml),
        epochs=50,
        imgsz=640,
        batch=8,
        name="plate_yolo",
        patience=15,
        project=str(RUNS_DIR),
    )
    logger.info("학습 완료")

    # best.pt → services/plate_yolo.pt 복사
    best_pt = _find_best_pt()
    shutil.copy(str(best_pt), str(OUTPUT_MODEL))
    logger.info("모델 복사 완료: %s → %s", best_pt, OUTPUT_MODEL)

    print("\n" + "=" * 50)
    print(f"학습 완료")
    print(f"  best.pt 원본: {best_pt}")
    print(f"  서비스 모델:  {OUTPUT_MODEL}")
    print("=" * 50)


if __name__ == '__main__':
    main()
