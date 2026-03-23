import logging
import asyncio
import concurrent.futures
import cv2
import time
import uuid
import os
import re
import numpy as np
from datetime import datetime, timezone
from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

# OCR 전용 스레드풀: MJPEG 스트림 등 다른 asyncio.to_thread 작업과 분리
# max_workers=2: cpu_threads=2와 조합 시 동시 최대 4코어 사용 → YOLO 코어 확보
_ocr_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="paddle-ocr")

# 동시 OCR 작업 수 제한 (스레드풀 max_workers와 일치)
ocr_semaphore = asyncio.Semaphore(2)

# 한국어 번호판 규격 검증용 패턴
# 일반 번호판: 12가3456, 123가4567
# 구형 지역 번호판: 서울12가3456
PLATE_PATTERN = re.compile(r"^(\d{2,3}[가-힣]\d{4}|[가-힣]{2}\s?\d{2}[가-힣]\d{4})$")
CONFIDENCE_THRESHOLD = 0.60

NUMBERPLATE_DIR = "data/numberplate"
os.makedirs(NUMBERPLATE_DIR, exist_ok=True)

logger.info("Initializing PaddleOCR model (Korean)...")
# Windows oneDNN 미구현 오류 방지
os.environ.setdefault("FLAGS_use_mkldnn", "0")
# 문서 방향 보정·비틀림 교정 비활성화 → dt_polys 좌표가 원본 이미지 기준으로 반환
ocr_model = PaddleOCR(
    lang='korean',
    use_angle_cls=False,
    enable_mkldnn=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    cpu_threads=2,          # OCR 전용 코어 2개로 제한 → YOLO/MJPEG 코어 경쟁 방지
)


def _normalize_ocr_result(result) -> list | None:
    """PaddleOCR 결과를 구버전 형식 [[bbox, (text, conf)], ...] 으로 정규화.

    PaddleOCR 2.x(구) 형식: result[0] = [[bbox_points, (text, conf)], ...]
    PaddleX 기반 신형식:     result[0] = {'dt_polys': [...], 'rec_texts': [...], 'rec_scores': [...]}
    """
    if not result:
        return None

    first = result[0]

    # 신형식 (dict)
    if isinstance(first, dict):
        polys  = first.get('dt_polys',   [])
        texts  = first.get('rec_texts',  [])
        scores = first.get('rec_scores', [])
        if not polys:
            return None
        lines = []
        for poly, text, score in zip(polys, texts, scores):
            bbox = poly.tolist() if hasattr(poly, 'tolist') else list(poly)
            lines.append([bbox, [text, float(score)]])
        return lines if lines else None

    # 구형식 (list) — 그대로 반환
    return first if first else None


def _preprocess_for_ocr(img: np.ndarray, binarize: bool = False) -> np.ndarray:
    """번호판 이미지 OCR 전처리: 최소 크기 보장 → 그레이스케일 → CLAHE → (선택) 이진화+팽창 → 3ch

    Args:
        binarize: True이면 OTSU 이진화+팽창 적용 (크롭된 번호판에만 사용),
                  False이면 CLAHE만 적용 (전체 이미지 탐지용)
    """
    h, w = img.shape[:2]
    if w < 600:
        scale = 600 / w
        img = cv2.resize(img, (600, int(h * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(gray)

    if binarize:
        # OTSU 이진화 + 팽창: 크롭된 번호판 최종 인식 시에만 사용
        _, enhanced = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((2, 2), np.uint8)
        enhanced = cv2.dilate(enhanced, kernel, iterations=1)

    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def _validate_crop(crop: np.ndarray) -> bool:
    """크롭 이미지가 번호판으로서 유효한 비율/크기인지 검증"""
    if crop is None or crop.size == 0:
        return False
    h, w = crop.shape[:2]
    ratio = w / max(h, 1)
    return w >= 40 and h >= 10 and 1.2 <= ratio <= 9.0


def _brighten_frame(img: np.ndarray) -> np.ndarray:
    """야간/어두운 이미지를 OCR에 적합하게 밝기 보정.
    평균 밝기가 80 미만이면 채널별 CLAHE를 강하게 적용한다."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    mean_brightness = float(gray.mean())
    if mean_brightness >= 80:
        return img
    # 어두울수록 clipLimit을 높여 강하게 보정 (최대 8.0)
    clip = min(8.0, max(3.0, 120.0 / max(mean_brightness, 1.0)))
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    b, g, r = cv2.split(img)
    brightened = cv2.merge([clahe.apply(b), clahe.apply(g), clahe.apply(r)])
    logger.debug(f"[Brighten] mean={mean_brightness:.1f} → clipLimit={clip:.1f}")
    return brightened


def _find_plate_by_contour(frame: np.ndarray):
    """HSV 색상 기반 번호판 영역 탐지: 흰색·주황색·초록색 번호판 모두 대응"""
    bright = _brighten_frame(frame)
    gray = cv2.cvtColor(bright, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bright, cv2.COLOR_BGR2HSV)
    img_area = frame.shape[0] * frame.shape[1]

    # ① 흰색 번호판 (일반 승용차)
    white_mask = cv2.inRange(gray, 150, 255)
    # ② 주황/핑크 번호판 (트럭·구형 번호판)
    orange_mask = cv2.inRange(hsv, np.array([5, 60, 80]), np.array([28, 255, 255]))
    # ③ 초록 번호판 (전기차)
    green_mask = cv2.inRange(hsv, np.array([35, 50, 50]), np.array([90, 255, 255]))

    combined = cv2.bitwise_or(white_mask, cv2.bitwise_or(orange_mask, green_mask))
    kernel = np.ones((3, 3), np.uint8)
    combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h == 0:
            continue
        ratio = w / h
        area_ratio = (w * h) / img_area
        if 1.5 <= ratio <= 8.0 and 0.003 <= area_ratio <= 0.25 and w >= 50:
            candidates.append((area_ratio, x, y, w, h))

    if not candidates:
        return None

    candidates.sort(key=lambda c: abs(c[0] - 0.04))
    _, x, y, w, h = candidates[0]
    pad = 5
    crop = frame[max(0, y - pad):y + h + pad, max(0, x - pad):x + w + pad]
    return crop if _validate_crop(crop) else None


def _ocr_on_image(img: np.ndarray):
    """PaddleOCR 실행 → 번호판 패턴 bbox·텍스트 반환 (없으면 None)."""
    img_h, img_w = img.shape[:2]
    img_area = img_h * img_w

    raw = ocr_model.ocr(img)
    result = _normalize_ocr_result(raw)
    if not result:
        return None, None, 0.0, [], 0.0

    best_bbox = None
    best_text = None
    best_conf = 0.0
    best_score = 0.0
    fallback_texts = []
    fallback_conf_sum = 0.0

    for line in result:
        if not line or len(line) < 2 or not isinstance(line[1], (list, tuple)) or len(line[1]) < 2:
            continue
        bbox = line[0]
        text = line[1][0]
        conf = line[1][1]
        cleaned = re.sub(r'[^0-9가-힣]', '', text)
        fallback_texts.append(cleaned)
        fallback_conf_sum += conf

        # 1. bbox 비율·크기 검증 먼저 수행 (geometry 안 맞으면 버림)
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        bw = max(xs) - min(xs)
        bh = max(ys) - min(ys)
        if bh == 0:
            continue
        b_ratio = bw / bh
        b_area_ratio = (bw * bh) / max(img_area, 1)
        if not (1.2 <= b_ratio <= 9.0 and b_area_ratio <= 0.25 and bw >= 50 and bh >= 10):
            logger.debug("[OCR] bbox 미통과: %s ratio=%.2f area=%.3f", cleaned, b_ratio, b_area_ratio)
            continue

        # 2. 정규식 일치 여부는 가산점(+1.0)으로만 활용 → 최적 bbox 선정
        is_perfect_match = PLATE_PATTERN.match(cleaned) is not None
        score = conf + (1.0 if is_perfect_match else 0.0)

        if score > best_score:
            best_bbox = bbox
            best_text = cleaned
            best_score = score
            best_conf = conf

    avg_conf = fallback_conf_sum / len(result[0]) if result[0] else 0.0

    # ── 복합 매칭: OCR이 번호판을 여러 박스로 분리했을 때 합산하여 재시도 ──
    # (예: "120가" + "5871" → "120가5871")
    if best_bbox is None and result:
        valid_lines = []
        for line in result:
            if not (line and len(line) >= 2 and isinstance(line[1], (list, tuple)) and len(line[1]) >= 2):
                continue
            cleaned = re.sub(r'[^0-9가-힣]', '', line[1][0])
            if cleaned:  # 한국어/숫자 텍스트가 있는 라인만
                valid_lines.append((cleaned, line[0], line[1][1]))

        if len(valid_lines) >= 2:
            # x-center 기준 왼쪽→오른쪽 정렬
            valid_lines.sort(key=lambda t: sum(p[0] for p in t[1]) / 4)
            combined_text = "".join(t for t, _, _ in valid_lines)
            if PLATE_PATTERN.match(combined_text):
                # 텍스트 박스들의 영역을 하나의 bbox로 병합
                all_xs = [p[0] for _, bbox, _ in valid_lines for p in bbox]
                all_ys = [p[1] for _, bbox, _ in valid_lines for p in bbox]
                bw = max(all_xs) - min(all_xs)
                bh = max(all_ys) - min(all_ys)
                if bh > 0 and bw >= 20:
                    avg_c = sum(c for _, _, c in valid_lines) / len(valid_lines)
                    best_bbox = [
                        [min(all_xs), min(all_ys)], [max(all_xs), min(all_ys)],
                        [max(all_xs), max(all_ys)], [min(all_xs), max(all_ys)],
                    ]
                    best_text = combined_text
                    best_conf = avg_c
                    logger.debug("[OCR] 복합 박스 매칭: %s (avg_conf=%.3f)", combined_text, avg_c)

    return best_bbox, best_text, best_conf, fallback_texts, avg_conf


def _crop_from_bbox(src: np.ndarray, bbox, pad: int = 8):
    """bbox 좌표로 이미지를 크롭하고 절대 좌표를 함께 반환한다."""
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    x1 = max(0, int(min(xs)) - pad)
    y1 = max(0, int(min(ys)) - pad)
    x2 = min(src.shape[1], int(max(xs)) + pad)
    y2 = min(src.shape[0], int(max(ys)) + pad)
    return src[y1:y2, x1:x2], x1, y1, x2, y2


async def save_plate_image(frame: np.ndarray, plate_text: str, violation_type: str) -> str:
    """번호판 크롭 이미지를 data/numberplate/에 저장하고 상대경로를 반환한다."""
    if plate_text.startswith("UNRECOGNIZED") or not plate_text:
        filename = f"UNRECOGNIZED_{uuid.uuid4().hex[:8]}.jpg"
    else:
        # 파일명에 사용 불가능한 문자 제거
        safe_name = re.sub(r'[\\/:*?"<>|]', '_', plate_text)
        filename = f"{safe_name}.jpg"

    save_path = os.path.join(NUMBERPLATE_DIR, filename)

    def _write():
        # Windows에서 한글 경로 cv2.imwrite 미지원 → imencode + tofile 사용
        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        buf.tofile(save_path)

    await asyncio.to_thread(_write)
    logger.info(f"[Storage] Saved plate image: {save_path}")
    return f"numberplate/{filename}"


async def extract_license_plate(frame: np.ndarray) -> str:
    """
    [CPU/GPU 바운드] 영상 전처리 후 PaddleOCR 추출 및 정규식 정제/검증
    """
    async with ocr_semaphore:
        def _run_ocr():
            # 전처리 (최소 크기 보장 + CLAHE + 이진화 + 팽창)
            thresh_3channel = _preprocess_for_ocr(frame)

            # 전처리 완료 이미지로 추론 진행
            raw = ocr_model.ocr(thresh_3channel)
            result = _normalize_ocr_result(raw)
            if not result:
                return "UNRECOGNIZED"

            texts = []
            total_conf = 0.0

            for line in result:
                text = line[1][0]
                conf = line[1][1]
                texts.append(text)
                total_conf += conf

            raw_text = "".join(texts)
            cleaned_text = re.sub(r'[^0-9가-힣]', '', raw_text)
            avg_conf = total_conf / len(result[0])

            logger.info(f"[OCR Extracted] Cleaned: {cleaned_text} (Raw: {raw_text}), Conf: {avg_conf:.3f}")

            if avg_conf < CONFIDENCE_THRESHOLD:
                logger.warning(f"[OCR_FAIL: LOW_CONFIDENCE] {cleaned_text} scored {avg_conf:.3f}.")
                return f"MANUAL_REVIEW_REQUIRED:{cleaned_text}"

            if not PLATE_PATTERN.match(cleaned_text):
                logger.warning(f"[OCR_FAIL: REGEX_MISMATCH] {cleaned_text} does not match plate pattern.")
                return f"MANUAL_REVIEW_REQUIRED:{cleaned_text}"

            return cleaned_text

        try:
            plate_text = await asyncio.to_thread(_run_ocr)
            return plate_text
        except Exception as e:
            logger.error(f"[OCR] Exception during extraction: {e}")
            return "UNRECOGNIZED"


async def run_ocr_on_file(src_path: str) -> dict:
    """
    data/carnumber/ 이미지에서 PaddleOCR 감지 박스로 번호판 위치를 찾아
    해당 영역만 크롭 후 data/numberplate/에 저장한다.

    반환:
        plate_number: OCR 결과 (실패 시 "UNRECOGNIZED_{uuid[:8]}")
        image_url: data/numberplate/에 저장된 상대경로
        is_corrected: MANUAL_REVIEW 여부
    """
    def _read_image():
        # Windows에서 한글 경로 cv2.imread 미지원 → np.fromfile + imdecode 사용
        buf = np.fromfile(src_path, dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)

    frame = await asyncio.to_thread(_read_image)
    if frame is None:
        uid = uuid.uuid4().hex[:8]
        logger.warning(f"[OCR] 이미지 읽기 실패: {src_path}")
        return {"plate_number": f"UNRECOGNIZED_{uid}", "image_url": None, "is_corrected": False}

    # 밝기 보정된 프레임 (야간 이미지 대응) - 이후 Stage에서 재사용
    bright_frame = _brighten_frame(frame)

    # ── 1차 크롭: 하단 50% 범퍼 영역 타겟팅 (번호판 위치 집중) ──
    _bumper_y = int(frame.shape[0] * 0.50)
    bumper_frame = frame[_bumper_y:, :]
    bright_bumper = _brighten_frame(bumper_frame)
    logger.debug(f"[OCR 1차크롭] 전체 {frame.shape[0]}px → 범퍼 {bumper_frame.shape[0]}px (y≥{_bumper_y})")

    def _detect_plate_bbox():
        """4단계 전략으로 번호판 bbox 탐지 (1차 크롭된 범퍼 영역 기준)"""
        img_h, img_w = bumper_frame.shape[:2]

        # ── Stage -1: 전체 이미지 OCR ──
        # bumper 크롭 이전에 전체 frame 탐색 (번호판이 이미지 상단이거나 클로즈업 샷인 경우 대응)
        bbox_f, text_f, conf_f, _, _ = _ocr_on_image(frame)
        if bbox_f is not None:
            crop_f, *_ = _crop_from_bbox(frame, bbox_f, pad=8)
            if _validate_crop(crop_f):
                logger.info(f"[OCR Stage-1] 전체이미지 감지: {text_f} (conf={conf_f:.3f})")
                return crop_f, text_f, conf_f < CONFIDENCE_THRESHOLD

        # ── Stage 0: 밝기 기반 번호판 영역 사전 크롭 → 직접 OCR ──
        # 흰색 번호판은 어두운 차체/도로 배경에서 가장 밝은 수평 row
        # bumper_frame 전체 대신 번호판만 타겟팅하여 인식률 대폭 향상
        _s = bright_bumper[int(img_h * 0.05):int(img_h * 0.95), :]
        _gray_s = cv2.cvtColor(_s, cv2.COLOR_BGR2GRAY)
        _brightest_row = int(np.argmax(_gray_s.mean(axis=1)))
        _half_h = max(15, _s.shape[0] // 10)
        _r1 = max(0, _brightest_row - _half_h)
        _r2 = min(_s.shape[0], _brightest_row + _half_h)
        _x1, _x2 = int(img_w * 0.10), int(img_w * 0.90)
        _tight_crop = _s[_r1:_r2, _x1:_x2]

        if _validate_crop(_tight_crop):
            _prep = _preprocess_for_ocr(_tight_crop, binarize=True)
            _result0 = ocr_model.ocr(_prep)
            if _result0 and _result0[0]:
                _texts0, _confs0 = [], []
                for line in _result0[0]:
                    if line and len(line) >= 2 and isinstance(line[1], (list, tuple)):
                        _texts0.append(re.sub(r'[^0-9가-힣]', '', line[1][0]))
                        _confs0.append(line[1][1])
                _combined0 = "".join(_texts0)
                _avg_conf0 = sum(_confs0) / len(_confs0) if _confs0 else 0.0
                if PLATE_PATTERN.match(_combined0):
                    logger.info(f"[OCR Stage0] 밝기 크롭 직접 인식: {_combined0} (conf={_avg_conf0:.3f})")
                    return _tight_crop, _combined0, _avg_conf0 < CONFIDENCE_THRESHOLD
                # ── Stage 0b: 이진화 없이 재시도 (한글 획이 이진화로 뭉개진 경우 복원) ──
                _prep0b = _preprocess_for_ocr(_tight_crop, binarize=False)
                _result0b = ocr_model.ocr(_prep0b)
                if _result0b and _result0b[0]:
                    _texts0b, _confs0b = [], []
                    for _line0b in _result0b[0]:
                        if _line0b and len(_line0b) >= 2 and isinstance(_line0b[1], (list, tuple)):
                            _texts0b.append(re.sub(r'[^0-9가-힣]', '', _line0b[1][0]))
                            _confs0b.append(_line0b[1][1])
                    _combined0b = "".join(_texts0b)
                    _avg_conf0b = sum(_confs0b) / len(_confs0b) if _confs0b else 0.0
                    if PLATE_PATTERN.match(_combined0b):
                        logger.info(f"[OCR Stage0b] 비이진화 재시도 인식: {_combined0b} (conf={_avg_conf0b:.3f})")
                        return _tight_crop, _combined0b, _avg_conf0b < CONFIDENCE_THRESHOLD
                if _combined0:
                    logger.debug(f"[OCR Stage0] 부분 인식: {_combined0} — Stage1 진행")

        # ── Stage 1: 범퍼 영역 원본 컬러 OCR ──
        bbox, text, conf, fb_texts, avg_conf = _ocr_on_image(bumper_frame)
        if bbox is not None:
            crop, x1, y1, x2, y2 = _crop_from_bbox(bumper_frame, bbox)
            if _validate_crop(crop):
                logger.info(f"[OCR Stage1] 번호판 감지: {text} (conf={conf:.3f}, box={x1},{y1}-{x2},{y2})")
                return crop, text, conf < CONFIDENCE_THRESHOLD

        # ── Stage 1b: 밝기 보정 후 OCR (야간 이미지 대응) ──
        if bright_bumper is not bumper_frame:
            bbox1b, text1b, conf1b, fb_texts1b, avg_conf1b = _ocr_on_image(bright_bumper)
            if bbox1b is not None:
                crop1b, x1, y1, x2, y2 = _crop_from_bbox(bumper_frame, bbox1b)
                if _validate_crop(crop1b):
                    logger.info(f"[OCR Stage1b] 야간보정 감지: {text1b} (conf={conf1b:.3f})")
                    return crop1b, text1b, conf1b < CONFIDENCE_THRESHOLD
            fb_texts = fb_texts1b if fb_texts1b else fb_texts
            avg_conf = avg_conf1b if fb_texts1b else avg_conf

        # ── Stage 2: CLAHE 전처리 후 OCR 재시도 ──
        clahe_img = _preprocess_for_ocr(bright_bumper, binarize=False)
        bbox2, text2, conf2, fb_texts2, avg_conf2 = _ocr_on_image(clahe_img)
        if bbox2 is not None:
            crop2, x1, y1, x2, y2 = _crop_from_bbox(bumper_frame, bbox2)
            if _validate_crop(crop2):
                logger.info(f"[OCR Stage2] CLAHE 감지: {text2} (conf={conf2:.3f}, box={x1},{y1}-{x2},{y2})")
                return crop2, text2, conf2 < CONFIDENCE_THRESHOLD

        # ── Stage 3: HSV 색상 컨투어 기반 탐지 ──
        contour_crop = _find_plate_by_contour(bumper_frame)
        if contour_crop is not None:
            bbox3, text3, conf3, fb_texts3, avg_conf3 = _ocr_on_image(contour_crop)
            if text3 is not None:
                logger.info(f"[OCR Stage3] 컨투어 감지: {text3} (conf={conf3:.3f})")
                return contour_crop, text3, conf3 < CONFIDENCE_THRESHOLD
            # combined fallback 텍스트가 번호판 패턴에 맞으면 성공 처리
            combined3 = "".join(fb_texts3) if fb_texts3 else ""
            if PLATE_PATTERN.match(combined3):
                logger.info(f"[OCR Stage3] 컨투어 복합 감지: {combined3} (avg_conf={avg_conf3:.3f})")
                return contour_crop, combined3, avg_conf3 < CONFIDENCE_THRESHOLD
            if combined3:
                logger.info("[OCR Stage3] 컨투어 크롭 저장 (텍스트 미인식)")
                return contour_crop, f"MANUAL_REVIEW_REQUIRED:{combined3}", True

        # ── Stage 4: 슬라이딩 윈도우 — 핵심 2구역만 (성능 최적화) ──
        windows = [
            (0.45, 0.75),  # 일반 정면/트럭 정면
            (0.55, 0.90),  # 탑뷰·후면 통합
        ]
        for y_start, y_end in windows:
            y1 = int(img_h * y_start)
            y2 = int(img_h * y_end)
            region = bright_bumper[y1:y2, :]
            if region.size == 0:
                continue
            bboxW, textW, confW, fb_textsW, avg_confW = _ocr_on_image(region)
            if bboxW is not None and textW is not None:
                xs = [p[0] for p in bboxW]
                ys = [p[1] for p in bboxW]
                rx1 = max(0, int(min(xs)) - 8)
                ry1 = max(0, y1 + int(min(ys)) - 8)
                rx2 = min(img_w, int(max(xs)) + 8)
                ry2 = min(img_h, y1 + int(max(ys)) + 8)
                crop4 = bumper_frame[ry1:ry2, rx1:rx2]
                if _validate_crop(crop4):
                    logger.info(f"[OCR Stage4 {y_start:.0%}~{y_end:.0%}] 번호판: {textW} (conf={confW:.3f})")
                    return crop4, textW, confW < CONFIDENCE_THRESHOLD
            # Stage 4에서도 combined fallback 텍스트 패턴 매칭 시도
            combined4 = "".join(fb_textsW) if fb_textsW else ""
            if PLATE_PATTERN.match(combined4):
                # 윈도우 내에서 컨투어 재시도로 더 정밀한 크롭 시도
                contour_crop4 = _find_plate_by_contour(region)
                crop4_fb = contour_crop4 if (contour_crop4 is not None and _validate_crop(contour_crop4)) else bumper_frame[y1:y2, :]
                if _validate_crop(crop4_fb):
                    logger.info(f"[OCR Stage4 {y_start:.0%}~{y_end:.0%}] 복합 감지: {combined4} (avg_conf={avg_confW:.3f})")
                    return crop4_fb, combined4, avg_confW < CONFIDENCE_THRESHOLD

        # ── Fallback: 전체 이미지 텍스트 합산 반환 ──
        all_fb = fb_texts2 if fb_texts2 else fb_texts
        all_conf = avg_conf2 if fb_texts2 else avg_conf
        combined = "".join(all_fb)
        logger.warning(f"[OCR] 4단계 모두 실패 — fallback 텍스트: {combined} (avg_conf={all_conf:.3f})")
        if all_conf >= CONFIDENCE_THRESHOLD and combined:
            return None, f"MANUAL_REVIEW_REQUIRED:{combined}", True
        return None, "UNRECOGNIZED", False

    # OCR 전용 executor + 세마포어로 동시 실행 수 제한 (MJPEG 스트림 스레드 보호)
    async with ocr_semaphore:
        loop = asyncio.get_event_loop()
        plate_crop, plate_text_raw, is_corrected = await loop.run_in_executor(
            _ocr_executor, _detect_plate_bbox
        )

    if plate_text_raw.startswith("MANUAL_REVIEW_REQUIRED:"):
        plate_text = plate_text_raw.split(":", 1)[1]
        is_corrected = True
    else:
        plate_text = plate_text_raw

    if plate_crop is not None and _validate_crop(plate_crop):
        save_frame = plate_crop
    else:
        # 최후 폴백: 범퍼 영역에서 가장 밝은 행 중심으로 크롭 (탑뷰 대응)
        h = bumper_frame.shape[0]
        search_region = bright_bumper[int(h * 0.10):int(h * 0.90), :]
        gray_search = cv2.cvtColor(search_region, cv2.COLOR_BGR2GRAY)
        row_brightness = gray_search.mean(axis=1)
        brightest_row = int(np.argmax(row_brightness))
        half_height = max(20, search_region.shape[0] // 8)
        r1 = max(0, brightest_row - half_height)
        r2 = min(search_region.shape[0], brightest_row + half_height)
        abs_r1 = int(h * 0.10) + r1
        abs_r2 = int(h * 0.10) + r2
        w = bumper_frame.shape[1]
        x1_fb = int(w * 0.15)
        x2_fb = int(w * 0.85)
        candidate = bumper_frame[abs_r1:abs_r2, x1_fb:x2_fb]
        save_frame = candidate if _validate_crop(candidate) else bumper_frame[int(h * 0.10):int(h * 0.85), x1_fb:x2_fb]
        logger.info(f"[OCR] 최후 폴백 크롭 (범퍼 영역 밝은 행 기준 r={brightest_row})")

    image_url = await save_plate_image(save_frame, plate_text, "SPEEDING")
    return {"plate_number": plate_text, "image_url": image_url, "is_corrected": is_corrected}


async def process_violation_task(crop_frame: np.ndarray, violation_type: str, confidence: float):
    logger.info(f"Processing violation: {violation_type}...")

    # OCR 실행
    ocr_task = extract_license_plate(crop_frame)
    plate_text_raw = await ocr_task

    # MANUAL_REVIEW 접두사 처리: 접두사 제거 후 실제 값만 추출, is_corrected 플래그 세팅
    is_corrected = False
    if plate_text_raw.startswith("MANUAL_REVIEW_REQUIRED:"):
        plate_text = plate_text_raw.split(":", 1)[1]
        is_corrected = True
        logger.info(f"[OCR] Manual review required. Extracted value: {plate_text}")
    else:
        plate_text = plate_text_raw

    # 번호판 크롭 이미지 저장 (상대경로 반환)
    image_url = await save_plate_image(crop_frame, plate_text, violation_type)

    payload = {
        "eventId": f"TEST-{int(time.time())}-{uuid.uuid4().hex[:4]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cameraLocation": "테스트",
        "violationType": violation_type,
        "speedKmh": 0.0,
        "plateNumber": plate_text,
        "imageUrl": image_url,           # "numberplate/xxx.jpg" (프론트에서 prefix 추가)
        "isCorrected": is_corrected,
    }

    logger.info(f"[Violation Final] Plate: {plate_text} | Image: {image_url} | Manual: {is_corrected}")

    from services.webhook_client import webhook_client
    await webhook_client.send_violation(payload)

    return payload
