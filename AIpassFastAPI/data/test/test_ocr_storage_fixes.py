"""
Unit tests for ocr_storage.py — targeted at the three modified items:
  1. _validate_crop()         — relaxed size/ratio constraints
  2. save_plate_image()       — whitespace removal, forbidden-char deletion, dedup
  3. CONFIDENCE_THRESHOLD     — constant value assertion

PaddleOCR model initialisation is patched at import time so that no GPU/CPU
inference resources are required while the tests run.
"""
import os
import sys
import types
import importlib
import asyncio
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Patch PaddleOCR before importing the module under test so that the global
# `ocr_model = PaddleOCR(...)` line does not trigger model download/init.
# ---------------------------------------------------------------------------
_paddle_mock = MagicMock()
_paddle_mock.PaddleOCR.return_value = MagicMock()
sys.modules.setdefault("paddleocr", _paddle_mock)

# Also stub cv2 only if it is not already available (keeps real cv2 when present)
try:
    import cv2 as _cv2_check  # noqa: F401
except ImportError:
    _cv2_stub = types.ModuleType("cv2")
    _cv2_stub.imencode = MagicMock(return_value=(True, MagicMock(tofile=MagicMock())))
    sys.modules.setdefault("cv2", _cv2_stub)

# ---------------------------------------------------------------------------
# Import the module under test.  The working-directory must include the
# AIpassFastAPI root so that `services.ocr_storage` is on the Python path.
# ---------------------------------------------------------------------------
_FASTAPI_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if _FASTAPI_ROOT not in sys.path:
    sys.path.insert(0, _FASTAPI_ROOT)

import services.ocr_storage as ocr_storage  # noqa: E402
from services.ocr_storage import (  # noqa: E402
    _validate_crop,
    save_plate_image,
    CONFIDENCE_THRESHOLD,
    NUMBERPLATE_DIR,
)


# ===========================================================================
# Helper
# ===========================================================================

def _make_image(h: int, w: int) -> np.ndarray:
    """Return a solid grey BGR image of the given dimensions."""
    return np.full((h, w, 3), 128, dtype=np.uint8)


# ===========================================================================
# 1.  CONFIDENCE_THRESHOLD constant
# ===========================================================================

class TestConfidenceThreshold:
    def test_value_is_0_65(self):
        """CONFIDENCE_THRESHOLD must equal exactly 0.65 after the fix."""
        assert CONFIDENCE_THRESHOLD == 0.65

    def test_value_is_float(self):
        """Constant must be a float, not an int or string."""
        assert isinstance(CONFIDENCE_THRESHOLD, float)


# ===========================================================================
# 2.  _validate_crop()
# ===========================================================================

class TestValidateCrop:

    # --- None / empty inputs ------------------------------------------------

    def test_none_returns_false(self):
        """None input must be rejected."""
        assert _validate_crop(None) is False

    def test_empty_array_returns_false(self):
        """A zero-sized numpy array must be rejected."""
        assert _validate_crop(np.array([])) is False

    def test_zero_size_2d_array_returns_false(self):
        """A (0, 0, 3) shaped array must be rejected."""
        assert _validate_crop(np.zeros((0, 0, 3), dtype=np.uint8)) is False

    # --- Too-small images ---------------------------------------------------

    def test_width_below_minimum_returns_false(self):
        """w=19 (< 20) must be rejected regardless of height and ratio."""
        img = _make_image(h=30, w=19)  # ratio ~0.63 — out of range too, but width is the issue
        assert _validate_crop(img) is False

    def test_width_exactly_minimum_boundary(self):
        """w=20 is the minimum accepted width; height must still pass."""
        # ratio = 20/20 = 1.0 — within 0.8..12.0
        img = _make_image(h=20, w=20)
        assert _validate_crop(img) is True

    def test_height_below_minimum_returns_false(self):
        """h=7 (< 8) must be rejected."""
        img = _make_image(h=7, w=60)
        assert _validate_crop(img) is False

    def test_height_exactly_minimum_boundary(self):
        """h=8 is the minimum accepted height."""
        # ratio = 60/8 = 7.5 — within range
        img = _make_image(h=8, w=60)
        assert _validate_crop(img) is True

    # --- Ratio boundaries ---------------------------------------------------

    def test_ratio_below_lower_bound_returns_false(self):
        """ratio < 0.8 (too square / portrait) must be rejected."""
        # ratio = 10/20 = 0.5
        img = _make_image(h=20, w=10)
        assert _validate_crop(img) is False

    def test_ratio_at_lower_bound_is_accepted(self):
        """ratio == 0.8 is the minimum valid aspect ratio."""
        # 8*0.8 = 6.4 → use h=10, w=8  → ratio = 0.8 exactly
        img = _make_image(h=10, w=8)
        # w=8 < 20 → fails width check — need larger image to isolate ratio
        # h=25, w=20 → ratio = 0.8
        img = _make_image(h=25, w=20)
        assert _validate_crop(img) is True

    def test_ratio_at_upper_bound_is_accepted(self):
        """ratio == 12.0 is the maximum valid aspect ratio."""
        # h=10, w=120 → ratio = 12.0; both pass size checks
        img = _make_image(h=10, w=120)
        assert _validate_crop(img) is True

    def test_ratio_above_upper_bound_returns_false(self):
        """ratio > 12.0 (extremely wide) must be rejected."""
        # h=8, w=200 → ratio = 25.0
        img = _make_image(h=8, w=200)
        assert _validate_crop(img) is False

    # --- Typical licence plate dimensions -----------------------------------

    def test_typical_korean_plate_accepted(self):
        """Simulate a cropped Korean plate: roughly 520x110 px."""
        img = _make_image(h=110, w=520)
        assert _validate_crop(img) is True

    def test_nearly_square_small_plate_accepted(self):
        """Small crop with ratio just above lower bound must pass."""
        # ratio = 25/25 = 1.0; size passes
        img = _make_image(h=25, w=25)
        assert _validate_crop(img) is True

    # --- Extreme inputs beyond spec -----------------------------------------

    def test_single_pixel_image_returns_false(self):
        """1x1 image must be rejected (both size constraints fail)."""
        img = _make_image(h=1, w=1)
        assert _validate_crop(img) is False

    def test_large_image_wide_ratio_returns_false(self):
        """Very wide image (ratio > 12) must be rejected even if large."""
        img = _make_image(h=50, w=800)   # ratio = 16.0
        assert _validate_crop(img) is False


# ===========================================================================
# 3.  save_plate_image()
# ===========================================================================

@pytest.mark.asyncio
class TestSavePlateImage:
    """Tests for save_plate_image() focusing on filename sanitisation and dedup."""

    # Shared dummy frame (small grey image)
    _frame = _make_image(h=50, w=120)

    def _patch_write(self):
        """Return a context manager that stubs out the cv2 write path."""
        mock_buf = MagicMock()
        mock_buf.tofile = MagicMock()
        return patch("cv2.imencode", return_value=(True, mock_buf))

    def _patch_no_existing_file(self):
        """Patch os.path.exists to always return False (no pre-existing file)."""
        return patch("os.path.exists", return_value=False)

    def _patch_existing_file(self):
        """Patch os.path.exists to always return True (file already saved)."""
        return patch("os.path.exists", return_value=True)

    # --- Whitespace removal -------------------------------------------------

    async def test_space_in_plate_text_is_removed(self):
        """'12가 1234' must produce filename '12가1234.jpg'."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가 1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_tab_in_plate_text_is_removed(self):
        """Tab character within OCR result must be stripped."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가\t1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_newline_in_plate_text_is_removed(self):
        """Newline character within OCR result must be stripped."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가\n1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_multiple_spaces_are_all_removed(self):
        """Multiple consecutive spaces must all be stripped."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12 가  1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    # --- Forbidden character removal ----------------------------------------

    async def test_forward_slash_is_removed(self):
        """'12가/1234' must produce '12가1234.jpg' (no underscore substitution)."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가/1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_backslash_is_removed(self):
        r"""'12가\1234' must produce '12가1234.jpg'."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가\\1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_colon_is_removed(self):
        """Colon in plate text must be deleted."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가:1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_asterisk_is_removed(self):
        """Asterisk in plate text must be deleted."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가*1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_question_mark_is_removed(self):
        """Question mark in plate text must be deleted."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가?1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_double_quote_is_removed(self):
        """Double-quote in plate text must be deleted."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, '12가"1234', "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_angle_brackets_are_removed(self):
        """'<' and '>' in plate text must be deleted."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가<1234>", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_pipe_is_removed(self):
        """Pipe character in plate text must be deleted."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가|1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    async def test_combination_space_and_forbidden_char(self):
        """Space AND forbidden char together must both be removed cleanly."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "12가 /1234", "speeding")
        assert result == "numberplate/12가1234.jpg"

    # --- Duplicate prevention -----------------------------------------------

    async def test_existing_file_returns_cached_path_without_writing(self):
        """When the file already exists, the function must return immediately
        without calling cv2.imencode (no re-write)."""
        with patch("cv2.imencode") as mock_encode, self._patch_existing_file():
            result = await save_plate_image(self._frame, "12가1234", "speeding")
        mock_encode.assert_not_called()
        assert result == "numberplate/12가1234.jpg"

    async def test_existing_file_returns_correct_relative_path(self):
        """Duplicate path must use the 'numberplate/<name>' prefix."""
        with self._patch_write(), self._patch_existing_file():
            result = await save_plate_image(self._frame, "34나5678", "redlight")
        assert result.startswith("numberplate/")
        assert result.endswith(".jpg")

    # --- UNRECOGNIZED plates ------------------------------------------------

    async def test_unrecognized_prefix_generates_uuid_filename(self):
        """Plate text starting with 'UNRECOGNIZED' must keep UUID format."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "UNRECOGNIZED_abc123", "speeding")
        assert result.startswith("numberplate/UNRECOGNIZED_")
        assert result.endswith(".jpg")

    async def test_empty_plate_text_generates_unrecognized_filename(self):
        """Empty string plate_text must fall into the UNRECOGNIZED branch."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "", "speeding")
        assert result.startswith("numberplate/UNRECOGNIZED_")
        assert result.endswith(".jpg")

    # --- Normal clean plate -------------------------------------------------

    async def test_clean_plate_text_produces_correct_filename(self):
        """A clean, properly-formed plate must map to '<text>.jpg' unchanged."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "34나5678", "redlight")
        assert result == "numberplate/34나5678.jpg"

    async def test_return_value_starts_with_numberplate_prefix(self):
        """All returned paths must use the 'numberplate/' relative prefix."""
        with self._patch_write(), self._patch_no_existing_file():
            result = await save_plate_image(self._frame, "99아9999", "speeding")
        assert result.startswith("numberplate/")
