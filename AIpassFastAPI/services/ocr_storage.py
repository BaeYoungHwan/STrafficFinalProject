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

# 동시 OCR 작업 수 제한 — CPU 포화 방지
ocr_semaphore = asyncio.Semaphore(1)  # 동시 OCR 1개 제한 — CPU 포화 방지

# 한국어 번호판 규격 검증용 패턴
# 일반 번호판: 12가3456, 123가4567
# 구형 지역 번호판: 서울12가3456
_VALID_CHARS = r'[가나다라마바사아자카타파하거너더러머버서어저고노도로모보소오조구누두루무부수우주허호]'
PLATE_PATTERN = re.compile(
    rf"^(\d{{2,3}}{_VALID_CHARS}\d{{4}}|[가-힣]{{2}}\s?\d{{2}}{_VALID_CHARS}\d{{4}})$"
)
CONFIDENCE_THRESHOLD = 0.65

# OCR 오인식 교정 테이블: OCR이 잘못 읽은 문자 → 한글 후보 목록 (유사도 순)
_OCR_CORRECTION_MAP: dict[str, list[str]] = {
    "0": ["오", "호"],
    "1": ["이", "아"],
    "2": ["가", "나", "마"],
    "3": ["마", "바", "자"],
    "4": ["사"],
    "5": ["서", "아"],
    "6": ["거", "너"],
    "7": ["자"],
    "8": ["마", "하"],
    "9": ["구", "주", "호"],
    "D": ["다", "더"],
    "H": ["하", "허"],
    "U": ["우", "루"],
    "O": ["오", "호"],
    "Z": ["자", "조"],
    "E": ["어", "서"],
    "A": ["아", "나"],
    "T": ["타", "파"],
    "M": ["마", "머"],
    "B": ["바", "버"],
    "P": ["파", "포"],
    "G": ["거", "구"],
    "K": ["카", "크"],
    "N": ["나"],
    "S": ["서", "소", "수"],
    "R": ["라", "러"],
    "L": ["라", "루"],
    # 소문자 (PaddleOCR korean 모델이 소문자를 반환하는 케이스)
    "a": ["아", "사"],
    "b": ["바", "버"],
    "d": ["다", "더"],
    "e": ["어", "서"],
    "g": ["거", "구"],
    "h": ["하", "허"],
    "k": ["카"],
    "l": ["라", "루"],
    "m": ["마", "머"],
    "n": ["나", "너"],
    "o": ["오", "호"],
    "p": ["파", "포"],
    "q": ["아", "구"],
    "r": ["라", "러"],
    "s": ["서", "소", "수"],
    "t": ["타"],
    "u": ["우", "루"],
}

# 숫자 위치 영문자 → 숫자 교정 테이블
# 적용 시점: re.sub(r'[^0-9가-힣]', '') 이전에 실행해야 영문자가 탈락되지 않음
_LETTER_TO_DIGIT: dict[str, str] = {
    "O": "0",   # 원형 → 0
    "I": "1",   # 막대 → 1
    "l": "1",   # 소문자 L → 1
    "Z": "2",   # Z 굴곡 → 2
    "S": "5",   # S 형태 → 5
    "B": "8",   # B 쌍구멍 → 8
    "G": "6",   # G 굴곡 → 6
    "g": "9",   # 소문자 g → 9
    "o": "0",   # 소문자 o → 0
    "s": "5",   # 소문자 s → 5 (숫자 위치일 때)
    "b": "8",   # 소문자 b → 8 (숫자 위치일 때)
}


def _correct_digit_positions(text: str) -> str:
    """숫자여야 할 위치의 영문자를 _LETTER_TO_DIGIT 로 교정.

    한글이 포함된 텍스트: 한글 앞·뒤 숫자 세그먼트만 교정.
    한글 없는 텍스트: 전체 영문자 교정 (이후 _correct_ocr_text 에 위임).
    """
    if not text:
        return text
    if re.search(r'[가-힣]', text):
        # 한글 문자를 구분자로 분리하여 숫자 세그먼트만 교정
        parts = re.split(r'([가-힣])', text)
        return "".join(
            "".join(_LETTER_TO_DIGIT.get(c, c) for c in p)
            if not re.match(r'[가-힣]', p) else p
            for p in parts
        )
    return "".join(_LETTER_TO_DIGIT.get(c, c) for c in text)


def _correct_ocr_text(text: str) -> list[str]:
    """OCR 오인식 텍스트를 번호판 패턴 기반 위치 추정으로 교정하여 후보 목록 반환.

    번호판에서 한글이 위치해야 할 인덱스(2자리→index 2, 3자리→index 3)의
    문자가 _OCR_CORRECTION_MAP에 있을 경우 교정 후 PLATE_PATTERN 매칭 후보 반환.
    한글이 이미 포함된 텍스트는 교정 불필요하므로 빈 리스트 반환.
    """
    all_chars = re.sub(r'[^0-9a-zA-Z가-힣]', '', text)
    if re.search(r'[가-힣]', all_chars):
        return []
    m = re.match(r'^\d*', all_chars)
    leading = len(m.group()) if m else 0
    if leading not in (2, 3) or leading >= len(all_chars):
        return []
    char_at = all_chars[leading]
    if char_at not in _OCR_CORRECTION_MAP:
        return []
    candidates = []
    for repl in _OCR_CORRECTION_MAP[char_at]:
        corrected = re.sub(r'[^0-9가-힣]', '', all_chars[:leading] + repl + all_chars[leading + 1:])
        if PLATE_PATTERN.match(corrected):
            candidates.append(corrected)
    return candidates


# 유사 한글 혼동 교정 테이블 (획 모양이 비슷해서 OCR이 오인식하는 케이스)
_CONFUSABLE_HANGUL: dict[str, list[str]] = {
    "어": ["허", "서", "저"],
    "허": ["어", "서"],
    "오": ["호", "소"],
    "호": ["오", "소"],
    "아": ["하", "사"],
    "하": ["아"],
    "우": ["후", "수", "부"],
    "후": ["우"],
    "너": ["나", "머"],
    "나": ["너"],
    "머": ["마", "너"],
    "마": ["머"],
    "더": ["다", "버"],
    "다": ["더"],
    "버": ["바", "더"],
    "바": ["버"],
    "서": ["사", "어"],
    "사": ["서"],
    "저": ["자", "어"],
    "자": ["저"],
    "거": ["가"],
    "가": ["거"],
    "도": ["로", "고", "소"],
    "로": ["도", "고"],
    "고": ["도", "로", "호"],
    "노": ["도", "모"],
    "모": ["노", "도"],
    "보": ["소"],
    "조": ["소", "도"],
    "소": ["조", "도"],
    "구": ["수", "주"],
    "수": ["구"],
    "주": ["수", "구"],
    "누": ["두", "수"],
    "두": ["누"],
    "무": ["수", "누"],
    "루": ["수"],
    "부": ["수", "우"],
}


def _positional_hangul_recovery(raw_text: str) -> str | None:
    """번호판 구조 지식으로 한글 미인식/오인식 텍스트를 교정.

    한국 번호판 구조: [2-3자리 숫자][한글 1자리][4자리 숫자]
    한글이 있어야 할 위치의 문자를 집중적으로 교정.

    Args:
        raw_text: OCR 원본 텍스트 (영문 소문자 포함 가능)

    Returns:
        교정된 번호판 문자열 또는 None (교정 불가)
    """
    if not raw_text:
        return None

    # 유효 문자만 추출 (한글/숫자/영문)
    chars = re.sub(r'[^0-9a-zA-Z가-힣]', '', raw_text)
    if not chars:
        return None

    # 이미 PLATE_PATTERN 매칭이면 그대로 반환
    cleaned = re.sub(r'[^0-9가-힣]', '', _correct_digit_positions(chars))
    if PLATE_PATTERN.match(cleaned):
        return cleaned

    # 선두 숫자 개수 파악 → 한글 위치 추정
    m = re.match(r'^\d*', chars)
    leading = len(m.group()) if m else 0

    # 2자리와 3자리 모두 시도
    positions_to_try = []
    if leading in (2, 3):
        positions_to_try = [leading]
    elif leading == 4:
        # 4자리 숫자로 인식된 경우 → 2자리+한글+숫자 또는 3자리+한글+숫자 패턴 탐색
        positions_to_try = [2, 3]
    else:
        positions_to_try = [2, 3]

    for hangul_pos in positions_to_try:
        if hangul_pos >= len(chars):
            continue

        target_char = chars[hangul_pos]
        after_chars = chars[hangul_pos + 1:]
        # 뒤 숫자 부분 교정 (영문 → 숫자)
        after_corrected = _correct_digit_positions(after_chars)
        after_digits = re.sub(r'[^0-9]', '', after_corrected)

        prefix = re.sub(r'[^0-9]', '', chars[:hangul_pos])

        # Case 1: 이미 유효 한글인 경우
        if re.match(r'[가-힣]', target_char):
            candidate = prefix + target_char + after_digits
            if PLATE_PATTERN.match(candidate):
                return candidate
            # 유사 한글로 교차 교정 시도
            if target_char in _CONFUSABLE_HANGUL:
                for alt in _CONFUSABLE_HANGUL[target_char]:
                    alt_candidate = prefix + alt + after_digits
                    if PLATE_PATTERN.match(alt_candidate):
                        return alt_candidate

        # Case 2: ASCII → 한글 교정
        elif target_char in _OCR_CORRECTION_MAP:
            for hangul_candidate in _OCR_CORRECTION_MAP[target_char]:
                candidate = prefix + hangul_candidate + after_digits
                if PLATE_PATTERN.match(candidate):
                    return candidate

    return None


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
    det_db_thresh=0.2,      # 기본 0.3 → 희미한 문자도 감지
    det_db_box_thresh=0.4,  # 기본 0.5 → 작은 문자 bbox 생존
    rec_batch_num=6,        # 번호판 최대 6문자 일괄 처리
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


def _preprocess_for_ocr(
    img: np.ndarray,
    binarize: bool = False,
    scale_factor: float = 1.0,
    use_bilateral: bool = False,
    clahe_clip: float | None = None,
    binarize_method: str = "adaptive",
) -> np.ndarray:
    """번호판 이미지 OCR 전처리: 업스케일 → 그레이스케일 → bilateralFilter → CLAHE → (선택) 이진화+팽창 → 3ch

    Args:
        binarize: True이면 이진화+팽창 적용 (크롭된 번호판에만 사용),
                  False이면 CLAHE만 적용 (전체 이미지 탐지용)
        scale_factor: 1.0 초과 시 Lanczos4 업스케일 적용 (예: 2.0, 3.0, 4.0)
        use_bilateral: True이면 그레이스케일 후 bilateralFilter 적용
        clahe_clip: CLAHE clipLimit 고정값. None이면 이미지 표준편차 기반 자동 결정
        binarize_method: "adaptive"(기본, GAUSSIAN), "adaptive_mean", "otsu"
    """
    h, w = img.shape[:2]
    if scale_factor > 1.0:
        new_w = int(w * scale_factor)
        new_h = int(h * scale_factor)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        h, w = img.shape[:2]

    if w < 600:
        scale = 600 / w
        img = cv2.resize(img, (600, int(h * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    if use_bilateral:
        gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    tile_w = max(4, img.shape[1] // 8)
    tile_h = max(4, img.shape[0] // 4)
    if clahe_clip is not None:
        _clip = clahe_clip
    else:
        _std = float(gray.std())
        _clip = 4.0 if _std < 30 else (2.0 if _std < 60 else 1.5)
    clahe = cv2.createCLAHE(clipLimit=_clip, tileGridSize=(tile_w, tile_h))
    enhanced = clahe.apply(gray)

    # Unsharp Masking: 획 경계 강화 → PaddleOCR confidence 향상
    _gaussian = cv2.GaussianBlur(enhanced, (0, 0), 1.5)
    enhanced = cv2.addWeighted(enhanced, 1.8, _gaussian, -0.8, 0)

    if binarize:
        if binarize_method == "otsu":
            _, enhanced = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif binarize_method == "adaptive_mean":
            block = max(11, (enhanced.shape[0] // 4) | 1)
            enhanced = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, block, 10)
        else:  # "adaptive" — 기존 동작
            # Adaptive Gaussian Thresholding: 불균일 조명에도 한글 획 보존
            block = max(11, (enhanced.shape[0] // 4) | 1)  # 홀수 강제, 높이 비례
            enhanced = cv2.adaptiveThreshold(
                enhanced, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, block, 8
            )
        kernel = np.ones((2, 1), np.uint8)  # 세로 2px 팽창 → 한글 획 연결 보강
        enhanced = cv2.dilate(enhanced, kernel, iterations=1)

    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def _validate_crop(crop: np.ndarray) -> bool:
    """크롭 이미지가 번호판으로서 유효한 비율/크기인지 검증"""
    if crop is None or crop.size == 0:
        return False
    h, w = crop.shape[:2]
    ratio = w / max(h, 1)
    return w >= 20 and h >= 8 and 0.8 <= ratio <= 12.0


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


def _is_orange_plate(img: np.ndarray) -> bool:
    """주황/갈색 배경 번호판 여부 판정 (전체 픽셀 20% 이상이 주황 계열)"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([5, 50, 60]), np.array([32, 255, 255]))
    ratio = float(mask.sum()) / (255 * max(img.shape[0] * img.shape[1], 1))
    return ratio > 0.20


def _preprocess_orange_plate(img: np.ndarray) -> list[np.ndarray]:
    """주황 배경 특화 전처리 — LAB L채널 OTSU 이진화 3가지 변형 반환."""
    results = []
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 2))
    # 방법 1: LAB L채널 OTSU (주황↔흑 대비 극대화)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_ch = clahe.apply(lab[:, :, 0])
    _, l_bin = cv2.threshold(l_ch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(cv2.cvtColor(l_bin, cv2.COLOR_GRAY2BGR))
    # 방법 2: BGR→Gray OTSU
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, g_bin = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(cv2.cvtColor(g_bin, cv2.COLOR_GRAY2BGR))
    # 방법 3: 2x Lanczos + bilateralFilter + LAB L채널 OTSU
    img2x = cv2.bilateralFilter(
        cv2.resize(img, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4),
        9, 75, 75,
    )
    lab2x = cv2.cvtColor(img2x, cv2.COLOR_BGR2LAB)
    l2x = clahe.apply(lab2x[:, :, 0])
    _, l2x_bin = cv2.threshold(l2x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(cv2.cvtColor(l2x_bin, cv2.COLOR_GRAY2BGR))
    return results


def _find_plate_by_contour(frame: np.ndarray):
    """HSV 색상 기반 번호판 영역 탐지: 흰색·주황색·초록색 번호판 모두 대응"""
    bright = _brighten_frame(frame)
    gray = cv2.cvtColor(bright, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(bright, cv2.COLOR_BGR2HSV)
    img_area = frame.shape[0] * frame.shape[1]

    # ① 흰색 번호판 (일반 승용차)
    white_mask = cv2.inRange(gray, 150, 255)
    # ② 주황/핑크 번호판 (트럭·구형 번호판) — 채도 하한 완화(60→50): 조명 변화 대응
    orange_mask = cv2.inRange(hsv, np.array([5, 50, 60]), np.array([32, 255, 255]))
    # ③ 초록 번호판 (전기차)
    green_mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([90, 255, 255]))

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
        if 1.5 <= ratio <= 8.0 and 0.001 <= area_ratio <= 0.25 and w >= 50:
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
        text = _correct_digit_positions(text)
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
        if not (0.8 <= b_ratio <= 12.0 and b_area_ratio <= 0.35 and bw >= 20 and bh >= 8):
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
            cleaned = re.sub(r'[^0-9가-힣]', '', _correct_digit_positions(line[1][0]))
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
    if not plate_text:
        filename = f"UNRECOGNIZED_{uuid.uuid4().hex[:8]}.jpg"
    elif plate_text.startswith("UNRECOGNIZED"):
        # 이미 UUID가 포함된 plate_text를 그대로 파일명으로 사용 → DB 표시명과 파일명 일치
        filename = f"{plate_text}.jpg"
    else:
        # 1. 공백/탭/개행 제거 (OCR이 "12가 1234" 또는 "12가\n1234"로 반환하는 경우 대응)
        stripped = re.sub(r'\s+', '', plate_text)
        # 2. Windows 파일명 금지 문자 제거 (치환 대신 삭제 → 언더스코어 파일명 방지)
        safe_name = re.sub(r'[\\/:*?"<>|]', '', stripped)
        if not safe_name:
            safe_name = f"UNKNOWN_{uuid.uuid4().hex[:8]}"
        filename = f"{safe_name}.jpg"

    save_path = os.path.join(NUMBERPLATE_DIR, filename)

    # 동일 번호판 중복 저장 방지: 이미 파일이 존재하면 기존 경로 반환
    if os.path.exists(save_path):
        logger.info(f"[Storage] 이미 존재하는 번호판 이미지 재사용: {save_path}")
        return f"numberplate/{filename}"

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


def _detect_plate_by_ocr_clustering(frame: np.ndarray) -> tuple[np.ndarray | None, str, bool]:
    """OCR bbox들의 공간적 클러스터링으로 번호판 위치 역추적.

    YOLO가 실패한 전체 이미지에서 텍스트 bbox들을 행 단위로 클러스터링하여
    [숫자][한글/ASCII][숫자] 패턴과 매칭되는 행을 번호판 영역으로 사용.
    """
    h, w = frame.shape[:2]
    # 하단 65%만 탐색 (상단은 표지판 등 노이즈)
    y_offset = int(h * 0.35)
    search_area = frame[y_offset:, :]

    try:
        raw = ocr_model.ocr(search_area)
    except Exception as e:
        logger.debug(f"[OCR Cluster] OCR 실패: {e}")
        return None, "", True

    result = _normalize_ocr_result(raw)
    if not result:
        return None, "", True

    # bbox + text + conf 수집
    detections = []
    for line in result:
        if not (line and len(line) >= 2 and isinstance(line[1], (list, tuple))):
            continue
        bbox = line[0]
        text = str(line[1][0]) if line[1] else ""
        conf = float(line[1][1]) if len(line[1]) >= 2 else 0.0
        if not text:
            continue
        try:
            xs = [float(p[0]) for p in bbox]
            ys = [float(p[1]) for p in bbox]
        except (TypeError, IndexError):
            continue
        cx = (min(xs) + max(xs)) / 2
        cy = (min(ys) + max(ys)) / 2
        bh = max(ys) - min(ys)
        detections.append({
            "text": text, "conf": conf,
            "cx": cx, "cy": cy, "bh": bh,
            "x1": min(xs), "x2": max(xs),
            "y1": min(ys), "y2": max(ys),
        })

    if not detections:
        return None, "", True

    # y좌표 클러스터링: 같은 행의 텍스트 그룹화
    detections.sort(key=lambda d: d["cy"])
    rows = []
    current_row = [detections[0]]
    for d in detections[1:]:
        ref_bh = max(dd["bh"] for dd in current_row) or 10
        if abs(d["cy"] - current_row[-1]["cy"]) < ref_bh * 1.5:
            current_row.append(d)
        else:
            rows.append(current_row)
            current_row = [d]
    rows.append(current_row)

    # 각 행에서 번호판 패턴 탐색
    for row in rows:
        row.sort(key=lambda d: d["cx"])
        combined_text = "".join(d["text"] for d in row)

        # 교정 후 패턴 매칭
        corrected = _correct_digit_positions(combined_text)
        cleaned = re.sub(r'[^0-9가-힣]', '', corrected)
        plate_candidate = None

        if PLATE_PATTERN.match(cleaned):
            plate_candidate = cleaned
        # 주의: _positional_hangul_recovery를 여기서 호출하면 조기 반환으로
        # Stage 6 (고배율 정밀 인식)을 건너뛰어 오히려 정확도가 낮아질 수 있음.
        # 한글이 이미 포함된 경우만 Stage -1.5에서 반환하고,
        # 숫자만 있는 경우는 후속 스테이지에 위임한다.

        if plate_candidate:
            # 합산 bbox 계산 (padding 포함)
            pad = 15
            rx1 = max(0, int(min(d["x1"] for d in row)) - pad)
            ry1 = max(0, int(min(d["y1"] for d in row)) - pad)
            rx2 = min(search_area.shape[1], int(max(d["x2"] for d in row)) + pad)
            ry2 = min(search_area.shape[0], int(max(d["y2"] for d in row)) + pad)
            # 원본 frame 기준으로 y좌표 변환
            abs_y1 = y_offset + ry1
            abs_y2 = y_offset + ry2
            crop = frame[abs_y1:abs_y2, rx1:rx2]
            if not _validate_crop(crop):
                continue
            avg_conf = sum(d["conf"] for d in row) / len(row) if row else 0.0
            needs_review = avg_conf < CONFIDENCE_THRESHOLD or plate_candidate != cleaned
            logger.info(f"[OCR Cluster] 번호판 역추적 성공: '{combined_text}' → '{plate_candidate}' (conf={avg_conf:.3f})")
            return crop, plate_candidate, needs_review

    logger.debug(f"[OCR Cluster] 패턴 매칭 실패 (행 수: {len(rows)})")
    return None, "", True


async def run_ocr_on_file(src_path: str) -> dict:
    """
    data/carnumber/ 이미지에서 PaddleOCR 감지 박스로 번호판 위치를 찾아
    해당 영역만 크롭 후 data/numberplate/에 저장한다.

    반환:
        plate_number: OCR 결과 (실패 시 "UNRECOGNIZED_{uuid[:8]}")
        image_url: data/numberplate/에 저장된 상대경로
        needs_review: MANUAL_REVIEW 여부
    """
    def _read_image():
        # Windows에서 한글 경로 cv2.imread 미지원 → np.fromfile + imdecode 사용
        buf = np.fromfile(src_path, dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)

    frame = await asyncio.to_thread(_read_image)
    if frame is None:
        uid = uuid.uuid4().hex[:8]
        logger.warning(f"[OCR] 이미지 읽기 실패: {src_path}")
        return {"plate_number": f"UNRECOGNIZED_{uid}", "image_url": None, "needs_review": True}

    # 밝기 보정된 프레임 및 범퍼 크롭 — executor로 이동하여 이벤트 루프 차단 방지
    # bumper_y=0.35: 화물차 번호판이 이미지 중앙(~45%)에 위치하는 경우 대응
    def _preprocess_frames():
        bright = _brighten_frame(frame)
        bumper_y = int(frame.shape[0] * 0.35)
        bumper = frame[bumper_y:, :]
        bright_bmp = _brighten_frame(bumper)
        return bright, bumper_y, bumper, bright_bmp

    loop = asyncio.get_event_loop()
    bright_frame, _bumper_y, bumper_frame, bright_bumper = await loop.run_in_executor(
        _ocr_executor, _preprocess_frames
    )
    logger.debug(f"[OCR 1차크롭] 전체 {frame.shape[0]}px → 범퍼 {bumper_frame.shape[0]}px (y≥{_bumper_y})")

    def _detect_plate_bbox():
        """4단계 전략으로 번호판 bbox 탐지 (1차 크롭된 범퍼 영역 기준)"""
        img_h, img_w = bumper_frame.shape[:2]

        # ── Stage -2: YOLO 번호판 전용 모델 타이트 크롭 ──
        # 범용 PaddleOCR보다 정확한 번호판 영역 검출 → OCR 전처리 노이즈 최소화
        from services.plate_detector import detect_plate_crop
        yolo_crop = detect_plate_crop(frame)
        if yolo_crop is not None:
            # ── Stage -2O: 주황 번호판 특화 처리 ──
            if _is_orange_plate(yolo_crop):
                logger.info("[OCR Stage-2O] 주황 번호판 감지 → 특화 전처리 적용")
                for _orange_prep in _preprocess_orange_plate(yolo_crop):
                    _res_o = _normalize_ocr_result(ocr_model.ocr(_orange_prep))
                    if _res_o:
                        _t_o = [re.sub(r'[^0-9가-힣]', '', l[1][0])
                                for l in _res_o if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                        _c_o = [l[1][1] for l in _res_o if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                        _combined_o = "".join(_t_o)
                        if PLATE_PATTERN.match(_combined_o):
                            _conf_o = sum(_c_o) / len(_c_o) if _c_o else 0.0
                            logger.info("[OCR Stage-2O] 주황 번호판 인식: %s (conf=%.3f)", _combined_o, _conf_o)
                            return yolo_crop, _combined_o, _conf_o < CONFIDENCE_THRESHOLD
            # YOLO 크롭에 전처리 없는 컬러 직접 OCR 시도 (과전처리 회피)
            _res_y = _normalize_ocr_result(ocr_model.ocr(yolo_crop))
            if _res_y:
                _texts_y = []
                _confs_y = []
                for _l in _res_y:
                    if _l and len(_l) >= 2 and isinstance(_l[1], (list, tuple)):
                        _texts_y.append(re.sub(r'[^0-9가-힣]', '', _correct_digit_positions(_l[1][0])))
                        _confs_y.append(_l[1][1])
                _combined_y = "".join(_texts_y)
                _conf_y = sum(_confs_y) / len(_confs_y) if _confs_y else 0.0
                if PLATE_PATTERN.match(_combined_y):
                    logger.info("[OCR Stage-2] YOLO 크롭 직접 인식: %s (conf=%.3f)", _combined_y, _conf_y)
                    return yolo_crop, _combined_y, _conf_y < CONFIDENCE_THRESHOLD
                # 패턴 불일치 시 전처리 후 재시도 (Lanczos 2x 업스케일)
                _combined_y2 = ""  # Stage -2c 참조 안전성 보장
                _yolo_2x = cv2.resize(yolo_crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
                _res_y2 = _normalize_ocr_result(ocr_model.ocr(_yolo_2x))
                if _res_y2:
                    _texts_y2 = [re.sub(r'[^0-9가-힣]', '', _correct_digit_positions(_l[1][0]))
                                  for _l in _res_y2 if _l and len(_l) >= 2 and isinstance(_l[1], (list, tuple))]
                    _confs_y2 = [_l[1][1] for _l in _res_y2 if _l and len(_l) >= 2 and isinstance(_l[1], (list, tuple))]
                    _combined_y2 = "".join(_texts_y2)
                    _conf_y2 = sum(_confs_y2) / len(_confs_y2) if _confs_y2 else 0.0
                    if PLATE_PATTERN.match(_combined_y2):
                        logger.info("[OCR Stage-2b] YOLO 크롭 2x 인식: %s (conf=%.3f)", _combined_y2, _conf_y2)
                        return yolo_crop, _combined_y2, _conf_y2 < CONFIDENCE_THRESHOLD
                # ── Stage -2c: 한글 위치 교정 테이블 ──
                for _raw_y in [_combined_y, _combined_y2]:
                    if _raw_y:
                        _corr_y = _correct_ocr_text(_raw_y)
                        if _corr_y:
                            logger.info("[OCR Stage-2c] 한글위치교정: %s → %s", _raw_y, _corr_y[0])
                            return yolo_crop, _corr_y[0], _conf_y < CONFIDENCE_THRESHOLD

                # ── Stage -2d: OTSU/반전 전처리 변형 ──
                for _s2_inv, _s2_method in [(False, "otsu"), (True, "otsu"), (True, "adaptive")]:
                    _s2_base = cv2.bitwise_not(yolo_crop) if _s2_inv else yolo_crop
                    _s2_prep = _preprocess_for_ocr(_s2_base, binarize=True, scale_factor=2.0,
                                                    binarize_method=_s2_method)
                    _res_s2 = _normalize_ocr_result(ocr_model.ocr(_s2_prep))
                    if not _res_s2:
                        continue
                    _t_s2 = [re.sub(r'[^0-9가-힣]', '', _correct_digit_positions(_l[1][0]))
                              for _l in _res_s2 if _l and len(_l) >= 2 and isinstance(_l[1], (list, tuple))]
                    _c_s2 = [_l[1][1] for _l in _res_s2 if _l and len(_l) >= 2 and isinstance(_l[1], (list, tuple))]
                    _comb_s2 = "".join(_t_s2)
                    if PLATE_PATTERN.match(_comb_s2):
                        _conf_s2 = sum(_c_s2) / len(_c_s2) if _c_s2 else 0.0
                        logger.info("[OCR Stage-2d] YOLO 전처리: %s (inv=%s, %s, conf=%.3f)",
                                    _comb_s2, _s2_inv, _s2_method, _conf_s2)
                        return yolo_crop, _comb_s2, _conf_s2 < CONFIDENCE_THRESHOLD
                    _corr_s2 = _correct_ocr_text(_comb_s2)
                    if _corr_s2:
                        logger.info("[OCR Stage-2d+교정] %s → %s", _comb_s2, _corr_s2[0])
                        return yolo_crop, _corr_s2[0], True

                logger.debug("[OCR Stage-2] YOLO 크롭 OCR 패턴 불일치: %s — 기존 파이프라인 계속", _combined_y)

        # ── Stage -1.5: OCR bbox 클러스터링으로 번호판 위치 역추적 (YOLO 실패 시 보완) ──
        logger.debug("[OCR Stage-1.5] OCR bbox 클러스터링 번호판 검출 시도")
        _cluster_crop, _cluster_text, _cluster_review = _detect_plate_by_ocr_clustering(bumper_frame)
        if _cluster_crop is not None and _cluster_text:
            logger.info(f"[OCR Stage-1.5] 클러스터링 성공: {_cluster_text}")
            return _cluster_crop, _cluster_text, _cluster_review

        # ── Stage -1: 전체 이미지 OCR (상단 25% 제외) ──
        # bumper 크롭 이전에 전체 frame 탐색 (번호판이 이미지 상단이거나 클로즈업 샷인 경우 대응)
        # ※ 상단 25% 제외: 도로 표지판("종점" 등) 오탐 방지 — 번호판은 상단 최상부에 위치하지 않음
        # ※ PLATE_PATTERN 일치 시에만 즉시 반환 — 한글 누락 bbox로 조기 종료 방지
        # ※ 불일치 시에도 bbox/텍스트를 보존하여 최종 폴백으로 활용
        _s1_skip_top = int(frame.shape[0] * 0.25)
        _s1_frame = frame[_s1_skip_top:, :]
        bbox_f, text_f, conf_f, _, _ = _ocr_on_image(_s1_frame)
        _fb_stage_minus1_crop = None
        _fb_stage_minus1_text = None
        _fb_stage_minus1_conf = 0.0
        if bbox_f is not None and text_f:
            # bbox 좌표를 원본 frame 기준으로 보정
            bbox_f_orig = [[p[0], p[1] + _s1_skip_top] for p in bbox_f]
            crop_f, *_ = _crop_from_bbox(frame, bbox_f_orig, pad=8)
            if _validate_crop(crop_f):
                if PLATE_PATTERN.match(text_f):
                    logger.info(f"[OCR Stage-1] 전체이미지 감지: {text_f} (conf={conf_f:.3f})")
                    return crop_f, text_f, conf_f < CONFIDENCE_THRESHOLD
                # 패턴 불일치라도 부분 결과 보존 (한글 미인식 케이스 폴백용)
                logger.debug(f"[OCR Stage-1] 패턴 불일치 보존: {text_f} (conf={conf_f:.3f})")
                _fb_stage_minus1_crop = crop_f
                _fb_stage_minus1_text = text_f
                _fb_stage_minus1_conf = conf_f

        # ── Stage 0: 밝기 기반 번호판 영역 사전 크롭 → 직접 OCR ──
        # 흰색 번호판은 어두운 차체/도로 배경에서 가장 밝은 수평 row
        # bumper_frame 전체 대신 번호판만 타겟팅하여 인식률 대폭 향상
        _s = bright_bumper[int(img_h * 0.05):int(img_h * 0.95), :]
        _gray_s = cv2.cvtColor(_s, cv2.COLOR_BGR2GRAY)
        # 헤드라이트 글레어 억제: 230+ 픽셀 클리핑 후 row 탐색
        # 야간 이미지에서 헤드라이트(~255)가 argmax를 장악하는 문제 방지
        _gray_clipped = np.clip(_gray_s, 0, 220)
        _brightest_row = int(np.argmax(_gray_clipped.mean(axis=1)))
        _half_h = max(20, _s.shape[0] // 8)   # 기존 max(15, //10)에서 확대 → 더 넓은 행 포함
        _r1 = max(0, _brightest_row - _half_h)
        _r2 = min(_s.shape[0], _brightest_row + _half_h)
        _x1, _x2 = int(img_w * 0.10), int(img_w * 0.90)
        _tight_crop = _s[_r1:_r2, _x1:_x2]

        # ── Stage 0c: 전처리 없는 Lanczos 2x 컬러 직접 OCR (과전처리 회피 경로) ──
        if _tight_crop.size > 0 and _tight_crop.shape[0] >= 10 and _tight_crop.shape[1] >= 40:
            _color_2x = cv2.resize(_tight_crop, None, fx=2.0, fy=2.0,
                                    interpolation=cv2.INTER_LANCZOS4)
            _result_0c = _normalize_ocr_result(ocr_model.ocr(_color_2x))
            if _result_0c:
                _texts_0c = []
                _confs_0c = []
                for _l in _result_0c:
                    if _l and len(_l) >= 2 and isinstance(_l[1], (list, tuple)):
                        _texts_0c.append(re.sub(r'[^0-9가-힣]', '', _l[1][0]))
                        _confs_0c.append(_l[1][1])
                _combined_0c = "".join(_texts_0c)
                if PLATE_PATTERN.match(_combined_0c):
                    _conf_0c = sum(_confs_0c) / len(_confs_0c) if _confs_0c else 0.0
                    logger.info(f"[OCR Stage0c] 컬러 Lanczos 인식: {_combined_0c} (conf={_conf_0c:.3f})")
                    return _tight_crop, _combined_0c, _conf_0c < CONFIDENCE_THRESHOLD

        # ── Stage 0d: 어두운 배경 반전 OCR (야간 흰 글씨 → 검은 글씨로 변환) ──
        # 야간 이미지에서 흰 글씨가 OCR에서 숫자로 오인되는 문제 대응
        if _tight_crop.size > 0 and _tight_crop.shape[0] >= 10 and _tight_crop.shape[1] >= 40:
            _mean_bright = float(cv2.cvtColor(_tight_crop, cv2.COLOR_BGR2GRAY).mean())
            if _mean_bright < 130:  # 어두운/중간 배경 판정 (100→130 확대: 청록 배경 대응)
                _inv_dark = cv2.bitwise_not(_tight_crop)
                for _dark_scale in [2.0, 3.0]:
                    _inv_scaled = cv2.resize(_inv_dark, None, fx=_dark_scale, fy=_dark_scale,
                                             interpolation=cv2.INTER_LANCZOS4)
                    _result_0d = _normalize_ocr_result(ocr_model.ocr(_inv_scaled))
                    if _result_0d:
                        _texts_0d = []
                        _confs_0d = []
                        for _l in _result_0d:
                            if _l and len(_l) >= 2 and isinstance(_l[1], (list, tuple)):
                                _texts_0d.append(re.sub(r'[^0-9가-힣]', '', _l[1][0]))
                                _confs_0d.append(_l[1][1])
                        _combined_0d = "".join(_texts_0d)
                        if PLATE_PATTERN.match(_combined_0d):
                            _conf_0d = sum(_confs_0d) / len(_confs_0d) if _confs_0d else 0.0
                            logger.info(f"[OCR Stage0d] 야간반전 {_dark_scale:.0f}x 인식: {_combined_0d} (conf={_conf_0d:.3f})")
                            return _tight_crop, _combined_0d, _conf_0d < CONFIDENCE_THRESHOLD

        # ※ _tight_crop은 가로로 긴 탐색 스트립 → 비율 검증(ratio≤9.0) 제외, 크기 검증만 수행
        _strip_ok = _tight_crop.size > 0 and _tight_crop.shape[0] >= 10 and _tight_crop.shape[1] >= 40
        if _strip_ok:
            # binarize=True → False 순으로 시도 (이진화 실패 시 한글 획 복원)
            for _binarize in [True, False]:
                _prep = _preprocess_for_ocr(_tight_crop, binarize=_binarize)
                _result0 = ocr_model.ocr(_prep)
                if not (_result0 and _result0[0]):
                    continue
                _texts0, _confs0, _bboxes0 = [], [], []
                for line in _result0[0]:
                    if line and len(line) >= 2 and isinstance(line[1], (list, tuple)):
                        _texts0.append(re.sub(r'[^0-9가-힣]', '', line[1][0]))
                        _confs0.append(line[1][1])
                        _bboxes0.append(line[0])
                _combined0 = "".join(_texts0)
                _avg_conf0 = sum(_confs0) / len(_confs0) if _confs0 else 0.0
                if PLATE_PATTERN.match(_combined0):
                    # OCR bbox로 정밀 크롭 재추출 (전체 스트립 대신 실제 번호판 영역)
                    if _bboxes0:
                        _all_xs = [p[0] for b in _bboxes0 for p in b]
                        _all_ys = [p[1] for b in _bboxes0 for p in b]
                        _cx1 = max(0, int(min(_all_xs)) + _x1 - 8)
                        _cy1 = max(0, int(min(_all_ys)) + _r1 + int(img_h * 0.05) - 8)
                        _cx2 = min(bumper_frame.shape[1], int(max(_all_xs)) + _x1 + 8)
                        _cy2 = min(bumper_frame.shape[0], int(max(_all_ys)) + _r1 + int(img_h * 0.05) + 8)
                        _refined = bumper_frame[_cy1:_cy2, _cx1:_cx2]
                        _crop0 = _refined if _validate_crop(_refined) else _tight_crop
                    else:
                        _crop0 = _tight_crop
                    _lbl = "Stage0" if _binarize else "Stage0b"
                    logger.info(f"[OCR {_lbl}] 밝기 크롭 인식: {_combined0} (conf={_avg_conf0:.3f})")
                    return _crop0, _combined0, _avg_conf0 < CONFIDENCE_THRESHOLD
            if _combined0:
                logger.debug(f"[OCR Stage0] 부분 인식: {_combined0} — Stage1 진행")

        # ── Stage 1: 범퍼 영역 원본 컬러 OCR ──
        bbox, text, conf, fb_texts, avg_conf = _ocr_on_image(bumper_frame)
        if bbox is not None and text and PLATE_PATTERN.match(text):
            crop, x1, y1, x2, y2 = _crop_from_bbox(bumper_frame, bbox)
            if _validate_crop(crop):
                logger.info(f"[OCR Stage1] 번호판 감지: {text} (conf={conf:.3f}, box={x1},{y1}-{x2},{y2})")
                return crop, text, conf < CONFIDENCE_THRESHOLD

        # ── Stage 1b: 밝기 보정 후 OCR (야간 이미지 대응) ──
        if bright_bumper is not bumper_frame:
            bbox1b, text1b, conf1b, fb_texts1b, avg_conf1b = _ocr_on_image(bright_bumper)
            if bbox1b is not None and text1b and PLATE_PATTERN.match(text1b):
                crop1b, x1, y1, x2, y2 = _crop_from_bbox(bumper_frame, bbox1b)
                if _validate_crop(crop1b):
                    logger.info(f"[OCR Stage1b] 야간보정 감지: {text1b} (conf={conf1b:.3f})")
                    return crop1b, text1b, conf1b < CONFIDENCE_THRESHOLD
            fb_texts = fb_texts1b if fb_texts1b else fb_texts
            avg_conf = avg_conf1b if fb_texts1b else avg_conf

        # ── Stage 1c: 야간 이미지 반전 OCR ──
        # 흰 글씨 + 어두운 배경 → 반전 → 검은 글씨 + 밝은 배경으로 OCR 정확도 향상
        # (헤드라이트 글레어로 Stage0이 실패하고 Stage1/1b도 실패한 경우 대응)
        _bumper_gray_mean = float(cv2.cvtColor(bumper_frame, cv2.COLOR_BGR2GRAY).mean())
        if _bumper_gray_mean < 110:
            _inv_bumper = cv2.bitwise_not(bumper_frame)
            bbox1c, text1c, conf1c, fb_texts1c, avg_conf1c = _ocr_on_image(_inv_bumper)
            if bbox1c is not None and text1c and PLATE_PATTERN.match(text1c):
                crop1c, x1, y1, x2, y2 = _crop_from_bbox(bumper_frame, bbox1c)
                if _validate_crop(crop1c):
                    logger.info(f"[OCR Stage1c] 야간반전 감지: {text1c} (conf={conf1c:.3f})")
                    return crop1c, text1c, conf1c < CONFIDENCE_THRESHOLD
            if fb_texts1c:
                fb_texts = fb_texts1c
                avg_conf = avg_conf1c

        # ── Stage 2: CLAHE 전처리 후 OCR 재시도 ──
        clahe_img = _preprocess_for_ocr(bright_bumper, binarize=False)
        bbox2, text2, conf2, fb_texts2, avg_conf2 = _ocr_on_image(clahe_img)
        if bbox2 is not None and text2 and PLATE_PATTERN.match(text2):
            crop2, x1, y1, x2, y2 = _crop_from_bbox(bumper_frame, bbox2)
            if _validate_crop(crop2):
                logger.info(f"[OCR Stage2] CLAHE 감지: {text2} (conf={conf2:.3f}, box={x1},{y1}-{x2},{y2})")
                return crop2, text2, conf2 < CONFIDENCE_THRESHOLD

        # ── Stage 3: HSV 색상 컨투어 기반 탐지 ──
        contour_crop = _find_plate_by_contour(bumper_frame)
        if contour_crop is not None:
            # ── Stage 3O: 주황 번호판 컨투어 크롭 특화 처리 ──
            if _is_orange_plate(contour_crop):
                for _orange_prep3 in _preprocess_orange_plate(contour_crop):
                    _res_o3 = _normalize_ocr_result(ocr_model.ocr(_orange_prep3))
                    if _res_o3:
                        _t_o3 = [re.sub(r'[^0-9가-힣]', '', l[1][0])
                                 for l in _res_o3 if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                        _c_o3 = [l[1][1] for l in _res_o3 if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                        _combined_o3 = "".join(_t_o3)
                        if PLATE_PATTERN.match(_combined_o3):
                            _conf_o3 = sum(_c_o3) / len(_c_o3) if _c_o3 else 0.0
                            logger.info("[OCR Stage3O] 컨투어 주황 인식: %s (conf=%.3f)", _combined_o3, _conf_o3)
                            return contour_crop, _combined_o3, _conf_o3 < CONFIDENCE_THRESHOLD
            # 3a: 크롭 원본 OCR
            bbox3, text3, conf3, fb_texts3, avg_conf3 = _ocr_on_image(contour_crop)
            if text3 is not None and PLATE_PATTERN.match(text3):
                logger.info(f"[OCR Stage3] 컨투어 감지: {text3} (conf={conf3:.3f})")
                return contour_crop, text3, conf3 < CONFIDENCE_THRESHOLD
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
            # 탑뷰 소형 번호판 대응: region 높이 80px 미만이면 2x Lanczos 업스케일
            _stage4_scale = 1.0
            if region.shape[0] < 80:
                region = cv2.resize(region, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
                _stage4_scale = 2.0
            bboxW, textW, confW, fb_textsW, avg_confW = _ocr_on_image(region)
            if bboxW is not None and textW is not None and PLATE_PATTERN.match(textW):
                xs = [p[0] / _stage4_scale for p in bboxW]
                ys = [p[1] / _stage4_scale for p in bboxW]
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

        # ── Stage 5: Stage-1 bbox 타이트 크롭 반전 OCR (야간 마 오인식 대응) ──
        # Stage-1이 번호판 bbox를 이미 찾았지만 한글을 숫자로 오인한 경우,
        # 해당 타이트 크롭을 반전(흰 글씨 → 검은 글씨)하여 재시도
        if _fb_stage_minus1_crop is not None and _validate_crop(_fb_stage_minus1_crop):
            _inv5 = cv2.bitwise_not(_fb_stage_minus1_crop)
            _inv5_2x = cv2.resize(_inv5, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_LANCZOS4)
            _res5 = _normalize_ocr_result(ocr_model.ocr(_inv5_2x))
            if _res5:
                _t5 = [re.sub(r'[^0-9가-힣]', '', l[1][0])
                        for l in _res5 if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                _c5 = [l[1][1] for l in _res5 if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                _combined5 = "".join(_t5)
                if PLATE_PATTERN.match(_combined5):
                    _conf5 = sum(_c5) / len(_c5) if _c5 else 0.0
                    logger.info(f"[OCR Stage5] Stage-1 크롭 반전 인식: {_combined5} (conf={_conf5:.3f})")
                    return _fb_stage_minus1_crop, _combined5, _conf5 < CONFIDENCE_THRESHOLD
                logger.info(f"[OCR Stage5] 패턴 불일치: {_combined5}")

        # ── Stage 6: 고배율(3x/4x) + bilateralFilter 전처리 ──
        # YOLO 크롭 또는 Stage-1 bbox 크롭에 대해 더 공격적인 전처리 시도
        _stage6_sources = []
        if yolo_crop is not None and _validate_crop(yolo_crop):
            _stage6_sources.append(("YOLO", yolo_crop))
        if _fb_stage_minus1_crop is not None and _validate_crop(_fb_stage_minus1_crop):
            _stage6_sources.append(("Stage-1", _fb_stage_minus1_crop))

        # 유사 혼동 한글 교정 테이블 (어두운 배경에서 ㅎ/ㅇ 상단 획 미인식으로 발생)
        _DARK_PLATE_SIMILAR: dict[str, str] = {"어": "허", "아": "하", "오": "호", "우": "후"}

        for _s6_name, _s6_src in _stage6_sources:
            _s6_gray_mean = cv2.cvtColor(_s6_src, cv2.COLOR_BGR2GRAY).mean()
            _s6_is_dark = _s6_gray_mean < 130
            # 어두운 배경 번호판: 반전 + bilateral 먼저 시도 (흰글씨→검은글씨)
            _s6_variants: list[tuple[str, np.ndarray]] = []
            if _s6_is_dark:
                _s6_variants.append(("inv", cv2.bitwise_not(_s6_src)))
            _s6_variants.append(("orig", _s6_src))

            for _s6_var_name, _s6_base in _s6_variants:
                # 2x 먼저 시도: artifact가 작을 때 덜 증폭됨 (선두 0 오인식 방지)
                for _s6_scale in [2.0, 3.0, 4.0]:
                    for _s6_binarize, _s6_method in [(False, "adaptive"), (True, "otsu")]:
                        _s6_prep = _preprocess_for_ocr(
                            _s6_base,
                            binarize=_s6_binarize,
                            scale_factor=_s6_scale,
                            use_bilateral=True,
                            binarize_method=_s6_method,
                        )
                        _res6 = _normalize_ocr_result(ocr_model.ocr(_s6_prep))
                        if not _res6:
                            continue
                        _t6 = [re.sub(r'[^0-9가-힣]', '', l[1][0])
                               for l in _res6 if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                        _c6 = [l[1][1] for l in _res6 if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                        _combined6 = "".join(_t6)
                        if not _combined6:
                            continue
                        _conf6 = sum(_c6) / len(_c6) if _c6 else 0.0
                        _lbl6 = f"Stage6{'-inv' if _s6_var_name=='inv' else ''}{'b' if _s6_binarize else ''}"

                        # ① 패턴 직접 매칭
                        if PLATE_PATTERN.match(_combined6):
                            logger.info(
                                "[OCR %s] %s %.0fx bilateral 인식: %s (conf=%.3f)",
                                _lbl6, _s6_name, _s6_scale, _combined6, _conf6,
                            )
                            # ── 선두 0 제거 후처리 ──
                            # 3자리 번호판이 0으로 시작하고 2자리 패턴도 유효한 경우 검증 시도
                            # (예: "023마8673" → "23마8673" 시도)
                            if re.match(r'^0\d{2}[가-힣]\d{4}$', _combined6):
                                _trimmed = _combined6[1:]  # 선두 "0" 제거
                                if PLATE_PATTERN.match(_trimmed):
                                    # 좌측 10% 제거 크롭으로 재검증
                                    _w6 = _s6_src.shape[1]
                                    _inner6 = _s6_src[:, int(_w6 * 0.10):]
                                    if _validate_crop(_inner6):
                                        _inner_prep = _preprocess_for_ocr(
                                            _inner6, scale_factor=3.0, use_bilateral=True)
                                        _res6i = _normalize_ocr_result(ocr_model.ocr(_inner_prep))
                                        if _res6i:
                                            _t6i = [re.sub(r'[^0-9가-힣]', '', l[1][0])
                                                    for l in _res6i if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                                            _combined6i = "".join(_t6i)
                                            if PLATE_PATTERN.match(_combined6i) and _combined6i == _trimmed:
                                                logger.info("[OCR %s] 선두0 제거 확인: %s → %s", _lbl6, _combined6, _combined6i)
                                                return _s6_src, _combined6i, _conf6 < CONFIDENCE_THRESHOLD
                            # ── 유사 한글 교정 시도 (패턴 매칭 내부 — 어→허 등 ㅎ/ㅇ 혼동 대응) ──
                            # 반전+고대비 CLAHE로 재확인: 어두운 배경에서 ㅎ 상단 획이 반전 후 더 선명
                            _s6_similar_found = False
                            for _orig_ch, _repl_ch in _DARK_PLATE_SIMILAR.items():
                                if _orig_ch in _combined6:
                                    _corrected6_cand = _combined6.replace(_orig_ch, _repl_ch, 1)
                                    if PLATE_PATTERN.match(_corrected6_cand):
                                        _s6_similar_found = True
                                        # 시도 1: _s6_base 반전 + 다중 CLAHE clip (5.0, 6.0)
                                        _inv_base = cv2.bitwise_not(_s6_base)
                                        for _clahe_try in [5.0, 6.0]:
                                            _hc_prep = _preprocess_for_ocr(
                                                _inv_base, scale_factor=_s6_scale,
                                                use_bilateral=True, clahe_clip=_clahe_try,
                                            )
                                            _res6_hc = _normalize_ocr_result(ocr_model.ocr(_hc_prep))
                                            if _res6_hc:
                                                _t6_hc = [re.sub(r'[^0-9가-힣]', '', l[1][0])
                                                          for l in _res6_hc if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                                                _combined6_hc = "".join(_t6_hc)
                                                if _combined6_hc == _corrected6_cand:
                                                    logger.info(
                                                        "[OCR %s] 유사한글 반전확인(clip=%.0f): %s → %s (conf=%.3f)",
                                                        _lbl6, _clahe_try, _combined6, _corrected6_cand, _conf6,
                                                    )
                                                    return _s6_src, _corrected6_cand, True  # needs_review=True
                                        # 시도 2: _s6_src 직접 반전 (base와 다를 경우 — inv variant에서 진입 시)
                                        if _s6_var_name == "orig":
                                            _inv_src = cv2.bitwise_not(_s6_src)
                                            for _extra_scale in [2.0, 3.0, 4.0]:
                                                _extra_prep = _preprocess_for_ocr(
                                                    _inv_src, scale_factor=_extra_scale, use_bilateral=True,
                                                )
                                                _res6_ex = _normalize_ocr_result(ocr_model.ocr(_extra_prep))
                                                if _res6_ex:
                                                    _t6_ex = [re.sub(r'[^0-9가-힣]', '', l[1][0])
                                                              for l in _res6_ex if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
                                                    _combined6_ex = "".join(_t6_ex)
                                                    if _combined6_ex == _corrected6_cand:
                                                        logger.info(
                                                            "[OCR %s] 유사한글 반전src확인(%.0fx): %s → %s (conf=%.3f)",
                                                            _lbl6, _extra_scale, _combined6, _corrected6_cand, _conf6,
                                                        )
                                                        return _s6_src, _corrected6_cand, True
                            # 유사 한글이 확인 없이 남아 있으면 검토 플래그 설정 (어/허 혼동 가능)
                            _s6_nr = _s6_similar_found or (_conf6 < CONFIDENCE_THRESHOLD)
                            if _s6_similar_found:
                                logger.info(
                                    "[OCR %s] 유사한글 포함 검토요청: %s (확인 불가)", _lbl6, _combined6,
                                )
                            return _s6_src, _combined6, _s6_nr

        # ── Stage 7: OCR 교정 테이블 기반 재매칭 ──
        # 부분 인식된 텍스트에 _correct_ocr_text 적용 → PLATE_PATTERN 재매칭
        _stage7_partials: list[str] = []
        for _s7_source in [fb_texts2, fb_texts,
                           ([_fb_stage_minus1_text] if _fb_stage_minus1_text else [])]:
            if _s7_source:
                _stage7_partials.extend(t for t in _s7_source if t)
        for _s7_partial in _stage7_partials:
            _s7_corrections = _correct_ocr_text(_s7_partial)
            if _s7_corrections:
                _s7_crop = (
                    _fb_stage_minus1_crop
                    if (_fb_stage_minus1_crop is not None and _validate_crop(_fb_stage_minus1_crop))
                    else (_tight_crop if _strip_ok else None)
                )
                logger.info(
                    "[OCR Stage7] 교정 테이블 매칭: %s → %s",
                    _s7_partial, _s7_corrections[0],
                )
                return _s7_crop, _s7_corrections[0], True  # needs_review=True
        # 복합 텍스트 교정 시도
        _s7_combined = "".join(_stage7_partials)
        if _s7_combined:
            _s7_combined_corrections = _correct_ocr_text(_s7_combined)
            if _s7_combined_corrections:
                _s7_crop = (
                    _fb_stage_minus1_crop
                    if (_fb_stage_minus1_crop is not None and _validate_crop(_fb_stage_minus1_crop))
                    else (_tight_crop if _strip_ok else None)
                )
                logger.info(
                    "[OCR Stage7] 복합 교정: %s → %s",
                    _s7_combined, _s7_combined_corrections[0],
                )
                return _s7_crop, _s7_combined_corrections[0], True

        # ── Fallback: 전체 이미지 텍스트 합산 반환 ──
        all_fb = fb_texts2 if fb_texts2 else fb_texts
        all_conf = avg_conf2 if fb_texts2 else avg_conf
        combined = "".join(all_fb)
        logger.warning(f"[OCR] 4단계 모두 실패 — fallback 텍스트: {combined} (avg_conf={all_conf:.3f})")
        if all_conf >= CONFIDENCE_THRESHOLD and combined:
            return None, f"MANUAL_REVIEW_REQUIRED:{combined}", True
        # ── Stage -1 보존 결과 최후 활용 (번호판이 범퍼 영역 밖에 있는 경우) ──
        if _fb_stage_minus1_text:
            logger.warning(f"[OCR] Stage-1 부분 결과 활용: {_fb_stage_minus1_text} (conf={_fb_stage_minus1_conf:.3f})")
            return _fb_stage_minus1_crop, f"MANUAL_REVIEW_REQUIRED:{_fb_stage_minus1_text}", True
        return None, "UNRECOGNIZED", True

    # OCR 전용 executor + 세마포어로 동시 실행 수 제한 (MJPEG 스트림 스레드 보호)
    async with ocr_semaphore:
        plate_crop, plate_text_raw, needs_review = await loop.run_in_executor(
            _ocr_executor, _detect_plate_bbox
        )

    if plate_text_raw.startswith("MANUAL_REVIEW_REQUIRED:"):
        plate_text = plate_text_raw.split(":", 1)[1]
        needs_review = True
    else:
        plate_text = plate_text_raw

    # 한글 없는 결과(숫자만) 저장 차단 → 먼저 위치 기반 복구 시도
    if plate_text and not re.search(r'[가-힣]', plate_text) \
            and not plate_text.startswith("UNRECOGNIZED"):
        recovered = _positional_hangul_recovery(plate_text)
        if recovered:
            logger.info(f"[OCR] 한글 위치 복구 성공: {plate_text} → {recovered}")
            plate_text = recovered
            needs_review = True  # 복구된 결과는 운영자 검토 필요
        else:
            logger.warning(f"[OCR] 한글 없는 결과 차단: {plate_text} → UNRECOGNIZED 처리")
            plate_text = f"UNRECOGNIZED_{uuid.uuid4().hex[:8]}"
            needs_review = True

    if plate_crop is not None and _validate_crop(plate_crop):
        save_frame = plate_crop
    else:
        def _fallback_crop():
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
            x1_fb, x2_fb = int(w * 0.15), int(w * 0.85)
            candidate = bumper_frame[abs_r1:abs_r2, x1_fb:x2_fb]
            logger.info(f"[OCR] 최후 폴백 크롭 r={brightest_row}")
            return candidate if _validate_crop(candidate) else bumper_frame[int(h * 0.10):int(h * 0.85), x1_fb:x2_fb]

        save_frame = await loop.run_in_executor(_ocr_executor, _fallback_crop)

    image_url = await save_plate_image(save_frame, plate_text, "SPEEDING")
    return {"plate_number": plate_text, "image_url": image_url, "needs_review": needs_review}


async def process_violation_task(crop_frame: np.ndarray, violation_type: str, confidence: float):
    logger.info(f"Processing violation: {violation_type}...")

    # OCR 실행
    ocr_task = extract_license_plate(crop_frame)
    plate_text_raw = await ocr_task

    # MANUAL_REVIEW 접두사 처리: 접두사 제거 후 실제 값만 추출, needs_review 플래그 세팅
    needs_review = False
    if plate_text_raw.startswith("MANUAL_REVIEW_REQUIRED:"):
        plate_text = plate_text_raw.split(":", 1)[1]
        needs_review = True
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
        "needsReview": needs_review,
    }

    logger.info(f"[Violation Final] Plate: {plate_text} | Image: {image_url} | Manual: {needs_review}")

    from services.webhook_client import webhook_client
    await webhook_client.send_violation(payload)

    return payload
