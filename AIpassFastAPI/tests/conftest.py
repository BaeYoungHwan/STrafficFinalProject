"""
conftest.py — pytest 설정 및 공통 픽스처

PaddleOCR 모델 초기화를 테스트 실행 전에 패치하여 실제 모델 로딩을 방지한다.
sys.path에 AIpassFastAPI 루트를 추가하여 services 패키지를 임포트할 수 있게 한다.
"""
import sys
import os
import types
import numpy as np

# ── Python 경로: AIpassFastAPI 루트를 sys.path 맨 앞에 추가 ──
_FASTAPI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _FASTAPI_ROOT not in sys.path:
    sys.path.insert(0, _FASTAPI_ROOT)

# ── PaddleOCR 임포트 자체를 모킹 (실제 모델 로딩 방지) ──
# services/ocr_storage.py 최상위에서 `ocr_model = PaddleOCR(...)` 가 실행되므로
# 모듈이 임포트되기 전에 paddleocr 스텁을 sys.modules에 삽입해야 한다.
_paddle_stub = types.ModuleType("paddleocr")

class _FakePaddleOCR:
    def __init__(self, *args, **kwargs):
        pass
    def ocr(self, img):
        return [None]

_paddle_stub.PaddleOCR = _FakePaddleOCR
sys.modules.setdefault("paddleocr", _paddle_stub)

# ultralytics 스텁 (vision.py가 임포트될 경우 대비)
_ultra_stub = types.ModuleType("ultralytics")
class _FakeYOLO:
    def __init__(self, *args, **kwargs):
        pass
    def track(self, *args, **kwargs):
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.boxes = None
        return [mock_result]

_ultra_stub.YOLO = _FakeYOLO
sys.modules.setdefault("ultralytics", _ultra_stub)
