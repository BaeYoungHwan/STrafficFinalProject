"""
carnumber 이미지로 YOLO 번호판 어노테이션 자동 생성.
실행: cd AIpassFastAPI && python scripts/generate_annotations.py
"""
import os
import re
import logging
import random
import shutil
import yaml
from pathlib import Path

os.environ['GLOG_minloglevel'] = '3'
os.environ['FLAGS_logtostderr'] = '0'
logging.getLogger('ppocr').setLevel(logging.WARNING)
logging.getLogger('paddle').setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 경로 기준: scripts/ → 상위 = AIpassFastAPI/
ROOT         = Path(__file__).resolve().parent.parent
CARNUMBER_DIR = ROOT / "data" / "carnumber"
DATASET_DIR   = ROOT / "data" / "plate_dataset"

TRAIN_RATIO = 0.8
RANDOM_SEED = 42


def _clean_text(text: str) -> str:
    """숫자·한글만 남기고 나머지 제거."""
    return re.sub(r'[^0-9가-힣]', '', text)


def _bbox_to_yolo(bbox, img_w: int, img_h: int):
    """
    PaddleOCR bbox [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] → YOLO normalized (cx,cy,bw,bh).
    반환: (cx, cy, bw, bh) 모두 0~1 범위
    """
    xs = [pt[0] for pt in bbox]
    ys = [pt[1] for pt in bbox]
    x1, x2 = min(xs), max(xs)
    y1, y2 = min(ys), max(ys)

    cx = (x1 + x2) / 2.0 / img_w
    cy = (y1 + y2) / 2.0 / img_h
    bw = (x2 - x1) / img_w
    bh = (y2 - y1) / img_h

    # clamp to [0, 1]
    cx = max(0.0, min(1.0, cx))
    cy = max(0.0, min(1.0, cy))
    bw = max(0.0, min(1.0, bw))
    bh = max(0.0, min(1.0, bh))
    return cx, cy, bw, bh


def _yolo_valid(cx, cy, bw, bh) -> bool:
    """정규화 좌표가 유효한지 검증."""
    return (0.0 < bw <= 1.0) and (0.0 < bh <= 1.0) and \
           (0.0 <= cx <= 1.0) and (0.0 <= cy <= 1.0)


def _extract_detections(ocr_result):
    """
    PaddleOCR OCRResult(최신 포맷) 또는 구형 list-of-list 포맷 모두 처리.
    반환: list of (bbox_pts, text, conf)
        bbox_pts: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] 형태의 list(int)
    """
    detections = []
    if not ocr_result:
        return detections

    # 최신 PaddleOCR: result[0]이 OCRResult dict-like 객체
    first = ocr_result[0]
    if hasattr(first, 'keys'):
        # OCRResult: dt_polys, rec_texts, rec_scores 키 사용
        polys  = first.get('dt_polys',  []) or []
        texts  = first.get('rec_texts', []) or []
        scores = first.get('rec_scores',[]) or []
        for poly, text, score in zip(polys, texts, scores):
            # poly: numpy array shape (4,2)
            pts = [[int(p[0]), int(p[1])] for p in poly]
            detections.append((pts, text, float(score)))
        return detections

    # 구형 포맷: result[0] = list of [bbox, (text, conf)]
    if first is None:
        return detections
    for line in first:
        if line is None:
            continue
        try:
            bbox, (text, conf) = line
            pts = [[int(p[0]), int(p[1])] for p in bbox]
            detections.append((pts, text, float(conf)))
        except Exception:
            continue
    return detections


def _find_best_detection(ocr_result, stem: str, img_w: int, img_h: int, y_offset: int = 0):
    """
    ocr_result 에서 stem과 일치하는 detection 중 conf 최고값 반환.
    일치 없으면 None.
    반환: (cx, cy, bw, bh) 또는 None
    """
    best_conf = -1.0
    best_yolo = None

    for pts, text, conf in _extract_detections(ocr_result):
        cleaned = _clean_text(text)
        if cleaned != stem:
            continue

        # y_offset 보정 (하단 영역 슬라이싱 시 사용)
        adj_bbox = [[pt[0], pt[1] + y_offset] for pt in pts]
        yolo = _bbox_to_yolo(adj_bbox, img_w, img_h)
        if not _yolo_valid(*yolo):
            continue

        if conf > best_conf:
            best_conf = conf
            best_yolo = yolo

    return best_yolo


def process_image(ocr, img_path: Path):
    """
    단일 이미지 처리 → YOLO 좌표 반환.
    성공: (cx, cy, bw, bh), 실패: None
    """
    import numpy as np
    import cv2

    stem = img_path.stem  # 파일명 = 정답 번호판

    # 한글 경로 대응: fromfile → imdecode
    img_array = np.fromfile(str(img_path), dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        logger.warning("이미지 로드 실패: %s", img_path.name)
        return None

    h, w = img.shape[:2]

    # --- 1차 시도: 전체 이미지 ---
    result = ocr.ocr(img)
    yolo = _find_best_detection(result, stem, w, h, y_offset=0)
    if yolo is not None:
        return yolo

    # --- 2차 시도: 하단 50% 슬라이싱 ---
    y_start = h // 2
    bottom_half = img[y_start:, :]
    result2 = ocr.ocr(bottom_half)
    yolo2 = _find_best_detection(result2, stem, w, h, y_offset=y_start)
    if yolo2 is not None:
        logger.debug("하단 재시도 성공: %s", img_path.name)
        return yolo2

    return None


def main():
    import numpy as np  # noqa: F401 (import check)

    # ── 디렉토리 초기화 ──────────────────────────────────────────
    for split in ('train', 'val'):
        (DATASET_DIR / 'images' / split).mkdir(parents=True, exist_ok=True)
        (DATASET_DIR / 'labels' / split).mkdir(parents=True, exist_ok=True)

    # ── 이미지 목록 수집 ─────────────────────────────────────────
    exts = {'.jpg', '.jpeg', '.png', '.bmp'}
    all_images = [p for p in CARNUMBER_DIR.iterdir() if p.suffix.lower() in exts]
    if not all_images:
        logger.error("carnumber 이미지 없음: %s", CARNUMBER_DIR)
        return

    random.seed(RANDOM_SEED)
    random.shuffle(all_images)
    split_idx = int(len(all_images) * TRAIN_RATIO)
    train_imgs = all_images[:split_idx]
    val_imgs   = all_images[split_idx:]
    logger.info("전체 %d장  train=%d  val=%d", len(all_images), len(train_imgs), len(val_imgs))

    # ── PaddleOCR 초기화 ─────────────────────────────────────────
    logger.info("PaddleOCR 초기화 중...")
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(
        lang='korean',
        use_angle_cls=False,
        enable_mkldnn=False,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        cpu_threads=2,
    )
    logger.info("PaddleOCR 초기화 완료")

    # ── 어노테이션 생성 ──────────────────────────────────────────
    success, fail = 0, 0
    failed_files = []

    for split_name, imgs in [('train', train_imgs), ('val', val_imgs)]:
        for img_path in imgs:
            yolo = process_image(ocr, img_path)

            dst_img   = DATASET_DIR / 'images' / split_name / img_path.name
            dst_label = DATASET_DIR / 'labels' / split_name / (img_path.stem + '.txt')

            shutil.copy(str(img_path), str(dst_img))

            if yolo is not None:
                cx, cy, bw, bh = yolo
                dst_label.write_text(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n", encoding='utf-8')
                logger.info("[OK] %s → 0 %.4f %.4f %.4f %.4f", img_path.name, cx, cy, bw, bh)
                success += 1
            else:
                # 어노테이션 없는 경우 빈 txt (배경 이미지 취급)
                dst_label.write_text("", encoding='utf-8')
                logger.warning("[FAIL] %s — 일치 detection 없음", img_path.name)
                fail += 1
                failed_files.append(img_path.name)

    # ── data.yaml 생성 ───────────────────────────────────────────
    data_yaml = {
        'path': '.',
        'train': 'images/train',
        'val': 'images/val',
        'nc': 1,
        'names': ['plate'],
    }
    yaml_path = DATASET_DIR / 'data.yaml'
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data_yaml, f, allow_unicode=True, default_flow_style=False)
    logger.info("data.yaml 저장: %s", yaml_path)

    # ── 결과 요약 ────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"어노테이션 생성 완료")
    print(f"  성공: {success}건  /  실패: {fail}건  /  전체: {len(all_images)}건")
    if failed_files:
        print(f"  실패 파일 목록 ({len(failed_files)}개):")
        for name in failed_files:
            print(f"    - {name}")
    print("=" * 50)


if __name__ == '__main__':
    main()
