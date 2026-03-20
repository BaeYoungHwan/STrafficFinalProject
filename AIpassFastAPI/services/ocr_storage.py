import logging
import asyncio
import cv2
import time
import uuid
import os
import re
import numpy as np
from paddleocr import PaddleOCR
from core.config import settings
from utils.http_client import http_client

logger = logging.getLogger(__name__)

ocr_semaphore = asyncio.Semaphore(2)

# 한국어 번호판 규격 검증용 패턴
# 일반 번호판: 12가3456, 123가4567
# 구형 지역 번호판: 서울12가3456
PLATE_PATTERN = re.compile(r"^(\d{2,3}[가-힣]\d{4}|[가-힣]{2}\s?\d{2}[가-힣]\d{4})$")
CONFIDENCE_THRESHOLD = 0.80

NUMBERPLATE_DIR = "data/numberplate"
os.makedirs(NUMBERPLATE_DIR, exist_ok=True)

logger.info("Initializing PaddleOCR model (Korean)...")
ocr_model = PaddleOCR(lang='korean', use_angle_cls=False)


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
        cv2.imwrite(save_path, frame)

    await asyncio.to_thread(_write)
    logger.info(f"[Storage] Saved plate image: {save_path}")
    return f"numberplate/{filename}"


async def extract_license_plate(frame: np.ndarray) -> str:
    """
    [CPU/GPU 바운드] 영상 전처리 후 PaddleOCR 추출 및 정규식 정제/검증
    """
    async with ocr_semaphore:
        def _run_ocr():
            # 1. Grayscale 및 OTSU 이진화 전처리 (1-Channel)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh_frame = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 2. 팽창(dilate) 적용으로 문자 두께 보정
            kernel = np.ones((2, 2), np.uint8)
            thresh_frame = cv2.dilate(thresh_frame, kernel, iterations=1)

            # 3. 모델 주입을 위한 3-Channel(BGR) 형태 복원
            thresh_3channel = cv2.cvtColor(thresh_frame, cv2.COLOR_GRAY2BGR)

            # 4. 전처리 완료 이미지로 추론 진행
            result = ocr_model.ocr(thresh_3channel)
            if not result or not result[0]:
                return "UNRECOGNIZED"

            texts = []
            total_conf = 0.0

            for line in result[0]:
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
    data/carnumber/ 이미지 파일을 읽어 OCR 실행.
    기존 extract_license_plate, save_plate_image 함수를 재사용.

    반환:
        plate_number: OCR 결과 (실패 시 "UNRECOGNIZED_{uuid[:8]}")
        image_url: data/numberplate/에 저장된 상대경로
        is_corrected: MANUAL_REVIEW 여부
    """
    frame = await asyncio.to_thread(cv2.imread, src_path)
    if frame is None:
        uid = uuid.uuid4().hex[:8]
        logger.warning(f"[OCR] 이미지 읽기 실패: {src_path}")
        return {"plate_number": f"UNRECOGNIZED_{uid}", "image_url": None, "is_corrected": False}

    # 번호판 영역 크롭 (차량 이미지 하단 중앙)
    h, w = frame.shape[:2]
    crop_x1, crop_x2 = int(w * 0.20), int(w * 0.80)
    crop_y1, crop_y2 = int(h * 0.55), int(h * 0.90)
    plate_crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
    if plate_crop.size == 0:
        plate_crop = frame  # 크롭 실패 시 전체 이미지 사용
        logger.warning(f"[OCR] 번호판 크롭 실패, 전체 이미지 사용: {src_path}")

    plate_text_raw = await extract_license_plate(plate_crop)

    is_corrected = False
    if plate_text_raw.startswith("MANUAL_REVIEW_REQUIRED:"):
        plate_text = plate_text_raw.split(":", 1)[1]
        is_corrected = True
    else:
        plate_text = plate_text_raw

    # 크롭된 번호판 이미지를 numberplate에 저장
    image_url = await save_plate_image(plate_crop, plate_text, "SPEEDING")
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
        "violation_type": violation_type,
        "plate_number": plate_text,
        "image_url": image_url,
        "confidence": confidence,
        "is_corrected": is_corrected,
        "timestamp": int(time.time())
    }

    logger.info(f"[Violation Final] Plate: {plate_text} | Image: {image_url} | Manual: {is_corrected}")

    await http_client.send_payload("/api/v1/violations", payload)

    return payload
