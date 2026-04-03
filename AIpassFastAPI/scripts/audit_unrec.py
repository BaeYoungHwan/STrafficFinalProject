"""
UNRECOGNIZED 파일 OCR 감사
cd AIpassFastAPI && python scripts/audit_unrec.py
"""
import os, sys, cv2, numpy as np, re, io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['GLOG_minloglevel'] = '3'
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paddleocr import PaddleOCR
ocr = PaddleOCR(lang='korean', use_angle_cls=False, enable_mkldnn=False,
    use_doc_orientation_classify=False, use_doc_unwarping=False, cpu_threads=2)

PLATE_PATTERN = re.compile(r'^(\d{2,3}[가-힣]\d{4}|[가-힣]{2}\s?\d{2}[가-힣]\d{4})$')

def run_ocr(img):
    r = ocr.ocr(img)
    if not r or not r[0]: return '', 0.0
    first = r[0]
    if isinstance(first, dict):
        texts = first.get('rec_texts', [])
        scores = first.get('rec_scores', [])
    else:
        texts  = [l[1][0] for l in first if l and len(l)>=2 and isinstance(l[1],(list,tuple))]
        scores = [l[1][1] for l in first if l and len(l)>=2 and isinstance(l[1],(list,tuple))]
    combined = re.sub(r'[^0-9가-힣]', '', ''.join(texts))
    avg_conf = sum(scores)/len(scores) if scores else 0.0
    return combined, avg_conf

folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'numberplate')
unrec = sorted([f for f in os.listdir(folder) if f.startswith('UNRECOGNIZED')])

lines = []
lines.append(f'총 {len(unrec)}개 UNRECOGNIZED 파일 분석')

for f in unrec:
    path = os.path.join(folder, f)
    buf = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        lines.append(f'SKIP {f}')
        continue
    h, w = img.shape[:2]
    t1, c1 = run_ocr(img)
    img2x = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
    t2, c2 = run_ocr(img2x)
    inv3x = cv2.resize(cv2.bitwise_not(img), None, fx=3, fy=3, interpolation=cv2.INTER_LANCZOS4)
    t3, c3 = run_ocr(inv3x)
    best = max([(t1,c1),(t2,c2),(t3,c3)], key=lambda x: (PLATE_PATTERN.match(x[0]) is not None, x[1]))
    match_flag = 'MATCH' if PLATE_PATTERN.match(best[0]) else 'no'
    lines.append(f'{h}x{w} {f}')
    lines.append(f'  orig:{t1}({c1:.2f}) 2x:{t2}({c2:.2f}) inv3x:{t3}({c3:.2f}) -> best:{best[0]} [{match_flag}]')

lines.append('DONE')

# Write to file with UTF-8
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_unrec_result.txt')
with open(out_path, 'w', encoding='utf-8') as fp:
    fp.write('\n'.join(lines) + '\n')

# Also print
for l in lines:
    print(l, flush=True)
