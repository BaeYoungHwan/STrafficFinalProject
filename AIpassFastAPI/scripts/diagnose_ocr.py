"""
OCR 번호판 인식 실패 진단 스크립트

실행:
    cd AIpassFastAPI
    python scripts/diagnose_ocr.py 2>&1 | tee scripts/diagnose_report.txt

출력:
    - numberplate/ 불량 파일 목록 (한글 없음 or ≤5글자)
    - carnumber/ 전체에 대해 OCR 재실행 → PASS/FAIL 요약
"""

import os, sys, re, asyncio, logging
import numpy as np
import cv2

# 프로젝트 루트를 sys.path에 추가 (AIpassFastAPI 폴더에서 실행 기준)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PLATE_PATTERN = re.compile(r"^(\d{2,3}[가-힣]\d{4}|[가-힣]{2}\s?\d{2}[가-힣]\d{4})$")
HAN = re.compile(r"[가-힣]")

NUMBERPLATE_DIR = "data/numberplate"
CARNUMBER_DIR   = "data/carnumber"


# ─────────────────────────────────────────────────
# Step 1: numberplate/ 불량 파일 분석
# ─────────────────────────────────────────────────
def analyze_numberplate_dir():
    print("\n" + "="*60)
    print("[ Step 1 ] data/numberplate/ 불량 파일 분석")
    print("="*60)

    bad = []
    good = []
    for fname in sorted(os.listdir(NUMBERPLATE_DIR)):
        name = os.path.splitext(fname)[0]
        has_kor = bool(HAN.search(name))
        length  = len(name)
        is_valid = bool(PLATE_PATTERN.match(name))

        fpath = os.path.join(NUMBERPLATE_DIR, fname)
        buf   = np.fromfile(fpath, dtype=np.uint8)
        img   = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        shape = img.shape if img is not None else "UNREADABLE"

        tag = "OK " if (has_kor and length > 5) else "BAD"
        line = f"[{tag}] {fname:35s}  len={length:2d}  korean={has_kor}  valid={is_valid}  shape={shape}"
        print(line)

        if tag == "BAD":
            bad.append({"fname": fname, "name": name, "shape": shape})
        else:
            good.append(fname)

    print(f"\n  총 {len(good)+len(bad)}개 중 BAD={len(bad)}, OK={len(good)}")
    return bad


# ─────────────────────────────────────────────────
# Step 2: carnumber/ 전체 OCR 재실행
# ─────────────────────────────────────────────────
async def run_carnumber_diagnosis():
    print("\n" + "="*60)
    print("[ Step 2 ] data/carnumber/ OCR 재실행 (전체)")
    print("="*60)

    # ocr_storage 임포트 (PaddleOCR 초기화 포함 — 시간 소요)
    print("PaddleOCR 모델 로딩 중...")
    from services.ocr_storage import run_ocr_on_file

    files = sorted(os.listdir(CARNUMBER_DIR))
    results = []

    for fname in files:
        fpath = os.path.join(CARNUMBER_DIR, fname)
        print(f"\n[처리] {fname}")
        try:
            result = await run_ocr_on_file(fpath)
            plate   = result["plate_number"]
            img_url = result["image_url"]
            is_cor  = result["is_corrected"]
            has_kor = bool(HAN.search(plate))
            is_valid = bool(PLATE_PATTERN.match(plate))
            tag = "PASS" if (has_kor and is_valid) else "FAIL"
            print(f"  → [{tag}] plate='{plate}'  image='{img_url}'  corrected={is_cor}")
            results.append({
                "src": fname, "plate": plate,
                "tag": tag, "has_korean": has_kor, "is_valid": is_valid
            })
        except Exception as e:
            print(f"  → [ERR ] 예외 발생: {e}")
            results.append({"src": fname, "plate": "ERROR", "tag": "ERR", "has_korean": False, "is_valid": False})

    return results


# ─────────────────────────────────────────────────
# Step 3: 요약 리포트
# ─────────────────────────────────────────────────
def print_summary(bad_np, carnumber_results):
    print("\n" + "="*60)
    print("[ Step 3 ] 요약 리포트")
    print("="*60)

    print("\n▶ numberplate/ 불량 파일 (재확인):")
    for b in bad_np:
        print(f"  - {b['fname']:35s}  shape={b['shape']}")

    pass_count = sum(1 for r in carnumber_results if r["tag"] == "PASS")
    fail_count = sum(1 for r in carnumber_results if r["tag"] == "FAIL")
    err_count  = sum(1 for r in carnumber_results if r["tag"] == "ERR")

    print(f"\n▶ carnumber/ OCR 결과:")
    print(f"  PASS={pass_count}  FAIL={fail_count}  ERR={err_count}  총={len(carnumber_results)}")

    if fail_count > 0:
        print("\n  FAIL 목록:")
        for r in carnumber_results:
            if r["tag"] == "FAIL":
                print(f"    [FAIL] {r['src']:35s} → plate='{r['plate']}'  kor={r['has_korean']}  valid={r['is_valid']}")

    print("\n▶ 추정 근본 원인:")
    no_kor_fails = [r for r in carnumber_results if r["tag"] == "FAIL" and not r["has_korean"]]
    if no_kor_fails:
        print(f"  • 한글 미인식 ({len(no_kor_fails)}건): PaddleOCR가 한글 음절을 ASCII/숫자로 오인식하거나 탐지 자체를 누락")
        print("    → 예상 원인:")
        print("      1) OTSU 이진화로 한글 획 소실 (ocr_storage.py:92)")
        print("      2) _bumper_y=0.50 으로 번호판 일부가 상단 크롭에서 제외 (ocr_storage.py:355)")
        print("      3) bbox 비율 필터 1.2 하한으로 단일 한글 음절 bbox 탈락 (ocr_storage.py:200)")


# ─────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────
async def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"작업 디렉토리: {os.getcwd()}")

    bad_np = analyze_numberplate_dir()
    carnumber_results = await run_carnumber_diagnosis()
    print_summary(bad_np, carnumber_results)


if __name__ == "__main__":
    asyncio.run(main())
