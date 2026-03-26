"""
OCR 실패 원인 시각적 진단 스크립트

각 Stage별 중간 이미지를 data/debug/{파일명}/ 폴더에 저장하고
OCR 원시 결과(필터링 전)를 전부 출력하여 실패 원인을 특정한다.

실행:
    cd AIpassFastAPI
    python scripts/diagnose_visual.py

결과:
    - data/debug/{파일명}/ 폴더에 Stage별 중간 이미지 저장
    - 터미널에 Stage별 OCR 원시 결과 + 요약 리포트 출력
"""

import os
import sys
import re
import logging
import numpy as np
import cv2

# Windows cp949 콘솔에서 유니코드 출력 오류 방지
sys.stdout.reconfigure(encoding="utf-8", errors="replace") if hasattr(sys.stdout, "reconfigure") else None

# AIpassFastAPI 루트를 sys.path에 추가 (AIpassFastAPI 폴더에서 실행 기준)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── DEBUG 레벨 활성화: ocr_storage의 모든 logger.debug 메시지 출력 ──
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
# PaddleOCR 내부 로그는 WARNING 이상만 (너무 verbose)
logging.getLogger("ppocr").setLevel(logging.WARNING)
logging.getLogger("paddle").setLevel(logging.WARNING)
logger = logging.getLogger("diagnose_visual")

CARNUMBER_DIR = "data/carnumber"
DEBUG_DIR = "data/debug"
PLATE_PATTERN = re.compile(r"^(\d{2,3}[가-힣]\d{4}|[가-힣]{2}\s?\d{2}[가-힣]\d{4})$")
HAN = re.compile(r"[가-힣]")
CONFIDENCE_THRESHOLD = 0.60

# ─────────────────────────────────────────
# 유틸: 이미지 저장 (한글 경로 대응)
# ─────────────────────────────────────────
def save_img(path: str, img: np.ndarray):
    if img is None or img.size == 0:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    buf.tofile(path)


# ─────────────────────────────────────────
# 유틸: OCR 박스 시각화 (이미지에 박스+텍스트 그리기)
# ─────────────────────────────────────────
def draw_ocr_boxes(img: np.ndarray, raw_result) -> np.ndarray:
    vis = img.copy()
    if not raw_result or not raw_result[0]:
        return vis

    first = raw_result[0]
    # 신형식(dict) 정규화
    if isinstance(first, dict):
        polys  = first.get("dt_polys", [])
        texts  = first.get("rec_texts", [])
        scores = first.get("rec_scores", [])
        lines  = list(zip(polys, texts, scores))
    else:
        lines = [(line[0], line[1][0], line[1][1]) for line in first
                 if line and len(line) >= 2 and isinstance(line[1], (list, tuple))]

    for bbox, text, conf in lines:
        pts = np.array(bbox, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(vis, [pts], True, (0, 255, 0), 2)
        x, y = int(pts[:, 0, 0].min()), int(pts[:, 0, 1].min())
        label = f"{text[:12]} {conf:.2f}"
        cv2.putText(vis, label, (x, max(y - 4, 12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1, cv2.LINE_AA)
    return vis


# ─────────────────────────────────────────
# 단일 이미지 진단 (Stage별 이미지 저장 + OCR 원시 결과 출력)
# ─────────────────────────────────────────
def diagnose_one(src_path: str, ocr_model, _normalize_ocr_result,
                 _brighten_frame, _preprocess_for_ocr, _validate_crop,
                 _find_plate_by_contour):
    """carnumber 이미지 하나를 Stage별로 진단"""

    stem = os.path.splitext(os.path.basename(src_path))[0]
    out_dir = os.path.join(DEBUG_DIR, stem)
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'='*65}")
    print(f"[IMAGE] {stem}")
    print(f"{'='*65}")

    # ── 원본 읽기 ──
    buf = np.fromfile(src_path, dtype=np.uint8)
    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if frame is None:
        print("  [ERROR] 이미지 읽기 실패")
        return {"src": stem, "reason": "READ_ERROR", "plate": "ERROR"}

    save_img(os.path.join(out_dir, "00_original.jpg"), frame)
    print(f"  원본 크기: {frame.shape[1]}x{frame.shape[0]}")

    # ── 범퍼 크롭 (하단 50%) ──
    _bumper_y = int(frame.shape[0] * 0.50)
    bumper_frame = frame[_bumper_y:, :]
    bright_bumper = _brighten_frame(bumper_frame)
    save_img(os.path.join(out_dir, "01_bumper.jpg"), bumper_frame)
    save_img(os.path.join(out_dir, "01_bumper_bright.jpg"), bright_bumper)
    img_h, img_w = bumper_frame.shape[:2]
    print(f"  범퍼 크롭: y≥{_bumper_y} → {img_w}x{img_h}px")

    # ─────────────── Stage -1: 전체 이미지 직접 OCR ───────────────
    print("\n  [Stage -1] 전체 이미지 OCR")
    raw_full = ocr_model.ocr(frame)
    vis_full = draw_ocr_boxes(frame, raw_full)
    save_img(os.path.join(out_dir, "02_stage_minus1_full_ocr.jpg"), vis_full)
    _print_ocr_raw(raw_full, _normalize_ocr_result, "Stage-1(전체)")

    # ─────────────── Stage 0: 밝기 기반 타이트 크롭 ───────────────
    print("\n  [Stage 0] 밝기 기반 타이트 크롭")
    _s = bright_bumper[int(img_h * 0.05):int(img_h * 0.95), :]
    _gray_s = cv2.cvtColor(_s, cv2.COLOR_BGR2GRAY)
    _brightest_row = int(np.argmax(_gray_s.mean(axis=1)))
    _half_h = max(15, _s.shape[0] // 10)
    _r1 = max(0, _brightest_row - _half_h)
    _r2 = min(_s.shape[0], _brightest_row + _half_h)
    _x1, _x2 = int(img_w * 0.10), int(img_w * 0.90)
    tight_crop = _s[_r1:_r2, _x1:_x2]
    print(f"    밝기 최고 row={_brightest_row}, 크롭 y={_r1}~{_r2} x={_x1}~{_x2}")
    save_img(os.path.join(out_dir, "03_stage0_tight.jpg"), tight_crop)

    if _validate_crop(tight_crop):
        # binarize=True 버전 (Stage 0 실제 사용)
        prep_bin = _preprocess_for_ocr(tight_crop, binarize=True)
        save_img(os.path.join(out_dir, "04_stage0_binarized.jpg"), prep_bin)
        raw0 = ocr_model.ocr(prep_bin)
        vis0 = draw_ocr_boxes(prep_bin, raw0)
        save_img(os.path.join(out_dir, "04_stage0_binarized_ocr.jpg"), vis0)
        _print_ocr_raw(raw0, _normalize_ocr_result, "Stage0(이진화)", tight_crop)

        # binarize=False 버전 (Stage 0b 재시도)
        prep_nob = _preprocess_for_ocr(tight_crop, binarize=False)
        save_img(os.path.join(out_dir, "04b_stage0b_clahe.jpg"), prep_nob)
        raw0b = ocr_model.ocr(prep_nob)
        vis0b = draw_ocr_boxes(prep_nob, raw0b)
        save_img(os.path.join(out_dir, "04b_stage0b_clahe_ocr.jpg"), vis0b)
        _print_ocr_raw(raw0b, _normalize_ocr_result, "Stage0b(비이진화)", tight_crop)
    else:
        print("    → _validate_crop 실패: 타이트 크롭 크기/비율 미달")
        print(f"      크기: {tight_crop.shape[1]}x{tight_crop.shape[0]}" if tight_crop.size > 0 else "      크기: 0")

    # ─────────────── Stage 1: 범퍼 원본 OCR ───────────────
    print("\n  [Stage 1] 범퍼 영역 원본 OCR")
    raw1 = ocr_model.ocr(bumper_frame)
    vis1 = draw_ocr_boxes(bumper_frame, raw1)
    save_img(os.path.join(out_dir, "05_stage1_bumper_ocr.jpg"), vis1)
    _print_ocr_raw(raw1, _normalize_ocr_result, "Stage1(범퍼)")

    # ─────────────── Stage 1b: 밝기 보정 후 OCR ───────────────
    print("\n  [Stage 1b] 밝기 보정 범퍼 OCR")
    raw1b = ocr_model.ocr(bright_bumper)
    vis1b = draw_ocr_boxes(bright_bumper, raw1b)
    save_img(os.path.join(out_dir, "06_stage1b_bright_ocr.jpg"), vis1b)
    _print_ocr_raw(raw1b, _normalize_ocr_result, "Stage1b(야간보정)")

    # ─────────────── Stage 2: CLAHE 후 OCR ───────────────
    print("\n  [Stage 2] CLAHE 전처리 후 OCR")
    clahe_img = _preprocess_for_ocr(bright_bumper, binarize=False)
    save_img(os.path.join(out_dir, "07_stage2_clahe.jpg"), clahe_img)
    raw2 = ocr_model.ocr(clahe_img)
    vis2 = draw_ocr_boxes(clahe_img, raw2)
    save_img(os.path.join(out_dir, "07_stage2_clahe_ocr.jpg"), vis2)
    _print_ocr_raw(raw2, _normalize_ocr_result, "Stage2(CLAHE)")

    # ─────────────── Stage 3: HSV 컨투어 ───────────────
    print("\n  [Stage 3] HSV 컨투어 탐지")
    contour_crop = _find_plate_by_contour(bumper_frame)
    if contour_crop is not None:
        save_img(os.path.join(out_dir, "08_stage3_contour.jpg"), contour_crop)
        raw3 = ocr_model.ocr(contour_crop)
        vis3 = draw_ocr_boxes(contour_crop, raw3)
        save_img(os.path.join(out_dir, "08_stage3_contour_ocr.jpg"), vis3)
        _print_ocr_raw(raw3, _normalize_ocr_result, "Stage3(컨투어)", contour_crop)
    else:
        print("    → 컨투어 탐지 실패 (번호판 후보 없음)")

    # ─────────────── Stage 4: 슬라이딩 윈도우 ───────────────
    print("\n  [Stage 4] 슬라이딩 윈도우")
    for idx, (y_start, y_end) in enumerate([(0.45, 0.75), (0.55, 0.90)]):
        y1 = int(img_h * y_start)
        y2 = int(img_h * y_end)
        region = bright_bumper[y1:y2, :]
        if region.size == 0:
            continue
        save_img(os.path.join(out_dir, f"09_stage4_window{idx}.jpg"), region)
        raw4 = ocr_model.ocr(region)
        vis4 = draw_ocr_boxes(region, raw4)
        save_img(os.path.join(out_dir, f"09_stage4_window{idx}_ocr.jpg"), vis4)
        _print_ocr_raw(raw4, _normalize_ocr_result, f"Stage4(윈도우{idx} {y_start:.0%}~{y_end:.0%})", region)

    # ─────────────── 실제 run_ocr_on_file 최종 결과 ───────────────
    from services.ocr_storage import run_ocr_on_file
    import asyncio
    result = asyncio.run(run_ocr_on_file(src_path))
    plate    = result["plate_number"]
    img_url  = result["image_url"]
    is_cor   = result["needs_review"]
    has_kor  = bool(HAN.search(plate))
    is_valid = bool(PLATE_PATTERN.match(plate))

    # 최종 저장된 numberplate 이미지 복사
    if img_url:
        np_path = os.path.join("data", img_url)
        if os.path.exists(np_path):
            buf2 = np.fromfile(np_path, dtype=np.uint8)
            final_img = cv2.imdecode(buf2, cv2.IMREAD_COLOR)
            save_img(os.path.join(out_dir, "10_final_result.jpg"), final_img)

    tag = "PASS" if (has_kor and is_valid) else "FAIL"

    # 실패 이유 분류
    reason = _classify_reason(plate, has_kor, is_valid)
    print(f"\n  ★ 최종 결과: [{tag}] plate='{plate}'  url='{img_url}'  corrected={is_cor}")
    print(f"  ★ 실패 이유: {reason}")
    print(f"  ★ 디버그 이미지: {out_dir}/")

    return {"src": stem, "plate": plate, "tag": tag, "reason": reason, "has_kor": has_kor, "is_valid": is_valid}


def _print_ocr_raw(raw_result, _normalize_ocr_result, stage_label: str, ref_img: np.ndarray = None):
    """OCR 원시 결과를 필터링 전 전부 출력 (bbox 비율 계산 포함)"""
    result = _normalize_ocr_result(raw_result)
    if not result:
        print(f"    [{stage_label}] OCR 결과 없음 (텍스트 미탐지)")
        return

    ref_area = (ref_img.shape[0] * ref_img.shape[1]) if ref_img is not None else 1
    all_cleaned = []
    all_confs = []
    for line in result:
        if not (line and len(line) >= 2 and isinstance(line[1], (list, tuple)) and len(line[1]) >= 2):
            continue
        bbox = line[0]
        text = line[1][0]
        conf = float(line[1][1])
        cleaned = re.sub(r"[^0-9가-힣]", "", text)
        all_cleaned.append(cleaned)
        all_confs.append(conf)

        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        bw = max(xs) - min(xs)
        bh = max(ys) - min(ys)
        b_ratio = bw / bh if bh > 0 else 0
        b_area_ratio = (bw * bh) / max(ref_area, 1)

        bbox_ok = (1.2 <= b_ratio <= 9.0 and b_area_ratio <= 0.25 and bw >= 50 and bh >= 10)
        pat_ok  = bool(PLATE_PATTERN.match(cleaned))
        has_kor = bool(HAN.search(cleaned))

        flags = []
        if not bbox_ok:
            if bw < 50:
                flags.append(f"bw={bw:.0f}<50")
            if bh < 10:
                flags.append(f"bh={bh:.0f}<10")
            if not (1.2 <= b_ratio <= 9.0):
                flags.append(f"ratio={b_ratio:.2f}(1.2~9.0 밖)")
        if not has_kor:
            flags.append("한글없음")
        if conf < CONFIDENCE_THRESHOLD:
            flags.append(f"conf={conf:.2f}<{CONFIDENCE_THRESHOLD}")

        status = "✓" if (bbox_ok and pat_ok) else "✗"
        flag_str = f"  [{', '.join(flags)}]" if flags else ""
        print(f"    [{stage_label}] {status} '{text}' → '{cleaned}' conf={conf:.3f} "
              f"bw={bw:.0f} bh={bh:.0f} ratio={b_ratio:.2f}{flag_str}")

    combined = "".join(all_cleaned)
    avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.0
    pat_match = bool(PLATE_PATTERN.match(combined))
    print(f"    [{stage_label}] 합산: '{combined}' avg_conf={avg_conf:.3f} "
          f"PLATE_PATTERN={'✓' if pat_match else '✗'}")


def _classify_reason(plate: str, has_kor: bool, is_valid: bool) -> str:
    if plate.startswith("UNRECOGNIZED"):
        return "ALL_STAGES_FAIL"
    if plate.startswith("MANUAL_REVIEW_REQUIRED"):
        stripped = plate.split(":", 1)[1] if ":" in plate else plate
        if not HAN.search(stripped):
            return "KOREAN_MISSING"
        return "LOW_CONFIDENCE"
    if not has_kor:
        return "KOREAN_MISSING"
    if not is_valid:
        return "REGEX_MISMATCH"
    return "PASS"


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def main():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print(f"작업 디렉토리: {os.getcwd()}")

    print("\nPaddleOCR 모델 로딩 중 (최초 1회만 소요)...")
    from services.ocr_storage import (
        ocr_model, _normalize_ocr_result,
        _brighten_frame, _preprocess_for_ocr,
        _validate_crop, _find_plate_by_contour,
    )
    print("모델 로딩 완료.")

    files = sorted([
        f for f in os.listdir(CARNUMBER_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])
    print(f"\ncarnumber 이미지 {len(files)}개 진단 시작\n")

    results = []
    for fname in files:
        fpath = os.path.join(CARNUMBER_DIR, fname)
        res = diagnose_one(
            fpath, ocr_model, _normalize_ocr_result,
            _brighten_frame, _preprocess_for_ocr,
            _validate_crop, _find_plate_by_contour,
        )
        results.append(res)

    # ── 요약 리포트 ──
    print(f"\n{'='*65}")
    print("[ 요약 리포트 ]")
    print(f"{'='*65}")
    total = len(results)
    pass_  = [r for r in results if r["tag"] == "PASS"]
    fail_  = [r for r in results if r["tag"] == "FAIL"]
    err_   = [r for r in results if r["tag"] == "ERR"]
    print(f"  총 {total}건: PASS={len(pass_)}  FAIL={len(fail_)}  ERR={len(err_)}")

    if fail_:
        from collections import Counter
        reasons = Counter(r["reason"] for r in fail_)
        print("\n  실패 원인 분류:")
        for reason, cnt in reasons.most_common():
            print(f"    {reason}: {cnt}건")

        print("\n  FAIL 상세:")
        for r in fail_:
            kor_flag = "한글OK" if r["has_kor"] else "한글없음"
            print(f"    [FAIL][{r['reason']:20s}] {r['src']:35s} → '{r['plate']}'  {kor_flag}")

    print(f"\n  디버그 이미지: data/debug/ 폴더 확인")
    print(f"\n  ▶ 원인 추정 기준:")
    print(f"    KOREAN_MISSING  → OTSU 이진화(ocr_storage.py:92) 또는 bbox 비율 필터(ocr_storage.py:200) 의심")
    print(f"    ALL_STAGES_FAIL → 01_bumper.jpg에 번호판이 보이는지 확인 (_bumper_y=0.50 의심)")
    print(f"    LOW_CONFIDENCE  → 이미지 품질 또는 PaddleOCR 한국어 모델 한계")


if __name__ == "__main__":
    main()
