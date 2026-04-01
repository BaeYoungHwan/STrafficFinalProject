"""
저장된 UNRECOGNIZED 크롭에 직접 OCR - 모델 인식 능력 진단
cd AIpassFastAPI && python scripts/test_crop_ocr.py
"""
import os, sys, cv2, numpy as np, re

os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paddleocr import PaddleOCR
ocr = PaddleOCR(
    lang='korean', use_angle_cls=False, enable_mkldnn=False,
    use_doc_orientation_classify=False, use_doc_unwarping=False, cpu_threads=2
)


def run_ocr(img):
    r = ocr.ocr(img)
    if not r or not r[0]:
        return "", 0.0
    first = r[0]
    if isinstance(first, dict):
        texts = first.get('rec_texts', [])
        scores = first.get('rec_scores', [])
    else:
        texts  = [l[1][0] for l in first if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
        scores = [l[1][1] for l in first if l and len(l) >= 2 and isinstance(l[1], (list, tuple))]
    combined = re.sub(r'[^0-9가-힣]', '', ''.join(texts))
    avg_conf = sum(scores) / len(scores) if scores else 0.0
    return combined, avg_conf


TARGETS = [
    ("data/numberplate/UNRECOGNIZED_e69d3130.jpg",  "23마8673"),
    ("data/numberplate/UNRECOGNIZED_de222a92.jpg",  "200허3654"),
    ("data/numberplate/UNRECOGNIZED_da474568.jpg",  "006거9186"),
]

for path, expected in TARGETS:
    buf = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        print(f"[SKIP] {path} - 읽기 실패")
        continue
    h, w = img.shape[:2]
    print(f"\n{'='*55}")
    print(f"[대상] {path}  shape=({h}x{w})  기대={expected}")

    tests = {
        "원본 컬러": img,
        "2x Lanczos": cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4),
        "3x Lanczos": cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4),
        "3x + bilateral": cv2.bilateralFilter(
            cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4), 9, 75, 75),
        "반전": cv2.bitwise_not(img),
        "반전 2x": cv2.resize(cv2.bitwise_not(img), None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4),
        "반전 3x": cv2.resize(cv2.bitwise_not(img), None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4),
        "OTSU": (lambda g: cv2.cvtColor(cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1], cv2.COLOR_GRAY2BGR))(
            cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)),
        "LAB L 3x": (lambda lab: cv2.cvtColor(
            cv2.resize(
                cv2.threshold(cv2.createCLAHE(3.0,(4,2)).apply(lab[:,:,0]), 0, 255,
                              cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1],
                None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4),
            cv2.COLOR_GRAY2BGR))(cv2.cvtColor(img, cv2.COLOR_BGR2LAB)),
    }

    for name, t in tests.items():
        text, conf = run_ocr(t)
        match = "PASS" if text == expected.replace(" ", "") else ("NEAR" if expected.replace(" ", "") in text or text in expected.replace(" ", "") else "FAIL")
        print(f"  {match} [{name:20s}]  '{text}'  conf={conf:.3f}")
