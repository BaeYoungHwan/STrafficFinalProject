import logging
import asyncio
import cv2
import time
import uuid
import os
import re
import numpy as np
import boto3
from botocore.config import Config
from paddleocr import PaddleOCR
from core.config import settings
from utils.http_client import http_client

logger = logging.getLogger(__name__)

ocr_semaphore = asyncio.Semaphore(2)

# 한국어 번호판 규격 검증용 패턴
PLATE_PATTERN = re.compile(r"^\d{2,3}[가-힣]\d{4}$")
CONFIDENCE_THRESHOLD = 0.80

FALLBACK_DIR = "data/fallback_images"
os.makedirs(FALLBACK_DIR, exist_ok=True)

logger.info("Initializing PaddleOCR model (Korean)...")
ocr_model = PaddleOCR(use_angle_cls=True, lang='korean')

# s3_client = boto3.client('s3', region_name='ap-northeast-2', config=Config(signature_version='s3v4'))

async def upload_violation_image(frame_bytes: bytes, violation_type: str) -> str:
    s3_key = f"violations/{violation_type}_{int(time.time())}_{uuid.uuid4().hex[:6]}.jpg"
    
    def _s3_upload_and_presign():
        time.sleep(0.5) 
        return f"https://mock-s3.com/presigned/{s3_key}?sig=secure_token&expires=3600"

    def _save_local_fallback():
        safe_name = f"fallback_{uuid.uuid4().hex}.jpg"
        fallback_path = os.path.join(FALLBACK_DIR, safe_name)
        with open(fallback_path, "wb") as f:
            f.write(frame_bytes)
        return f"LOCAL_FALLBACK:{fallback_path}"

    try:
        url = await asyncio.wait_for(asyncio.to_thread(_s3_upload_and_presign), timeout=5.0)
        return url
    except (asyncio.TimeoutError, Exception) as e:
        logger.error(f"[Storage] Upload failed ({e}). Saving to safe fallback cache.")
        fallback_url = await asyncio.to_thread(_save_local_fallback)
        return fallback_url

async def extract_license_plate(frame: np.ndarray) -> str:
    """
    [CPU/GPU 바운드] 영상 전처리 후 PaddleOCR 추출 및 정규식 정제/검증
    """
    async with ocr_semaphore:
        def _run_ocr():
            # 1. Grayscale 및 OTSU 이진화 전처리 (1-Channel)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh_frame = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # 🚨 [QA 최종 반영] 2. 모델 주입을 위한 3-Channel(BGR) 형태 복원
            thresh_3channel = cv2.cvtColor(thresh_frame, cv2.COLOR_GRAY2BGR)

            # 3. 전처리 및 차원 복원이 완료된 이미지로 추론 진행
            result = ocr_model.ocr(thresh_3channel, cls=True)
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
                logger.warning(f"[OCR_FAIL: LOW_CONFIDENCE] {cleaned_text} scored {avg_conf:.3f}. Manual review required.")
                return f"MANUAL_REVIEW_REQUIRED:{cleaned_text}"
                
            if not PLATE_PATTERN.match(cleaned_text):
                logger.warning(f"[OCR_FAIL: REGEX_MISMATCH] {cleaned_text} does not match plate pattern. Manual review required.")
                return f"MANUAL_REVIEW_REQUIRED:{cleaned_text}"
                
            return cleaned_text
            
        try:
            plate_text = await asyncio.to_thread(_run_ocr)
            return plate_text
        except Exception as e:
            logger.error(f"[OCR] Exception during extraction: {e}")
            return "ERROR"

async def process_violation_task(crop_frame: np.ndarray, violation_type: str, confidence: float):
    logger.info(f"Processing violation: {violation_type}...")
    
    ret, buffer = await asyncio.to_thread(cv2.imencode, '.jpg', crop_frame)
    if not ret:
        return None
    frame_bytes = buffer.tobytes()

    upload_task = upload_violation_image(frame_bytes, violation_type)
    ocr_task = extract_license_plate(crop_frame)
    
    image_url, plate_text = await asyncio.gather(upload_task, ocr_task)
    
    payload = {
        "violation_type": violation_type,
        "plate_number": plate_text,
        "image_url": image_url,
        "confidence": confidence,
        "timestamp": int(time.time())
    }
    
    logger.info(f"[Violation Final] Plate: {plate_text} | Storage: {image_url[:40]}...")
    
    await http_client.send_payload("/api/v1/violations", payload)
    
    return payload