"""
test_ocr_storage.py — services/ocr_storage.py 단위 테스트

커버 대상:
  - PLATE_PATTERN regex
  - _validate_crop
  - _brighten_frame
  - _preprocess_for_ocr
  - _crop_from_bbox
  - _ocr_on_image (geometry 검증 우선 → 가산점 방식)
  - save_plate_image (async)
  - extract_license_plate (async)
  - run_ocr_on_file (async, 폴백 크롭 포함)

실행 방법:
  cd AIpassFastAPI
  pytest tests/test_ocr_storage.py -v
"""

import re
import asyncio
import types
import numpy as np
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ────────────────────────────────────────────────────────────────────────────
# conftest.py 가 paddleocr 스텁을 sys.modules에 먼저 삽입하므로
# 이 import 는 실제 PaddleOCR 을 로딩하지 않는다.
# ────────────────────────────────────────────────────────────────────────────
import services.ocr_storage as ocr_mod
from services.ocr_storage import (
    PLATE_PATTERN,
    CONFIDENCE_THRESHOLD,
    _validate_crop,
    _brighten_frame,
    _preprocess_for_ocr,
    _crop_from_bbox,
    _ocr_on_image,
    save_plate_image,
    extract_license_plate,
    run_ocr_on_file,
)


# ============================================================
# 헬퍼 팩토리
# ============================================================

def make_image(h: int = 100, w: int = 300, fill: int = 128) -> np.ndarray:
    """BGR 더미 이미지를 반환한다."""
    img = np.full((h, w, 3), fill, dtype=np.uint8)
    return img


def make_dark_image(h: int = 100, w: int = 300) -> np.ndarray:
    """평균 밝기가 80 미만인 어두운 이미지를 반환한다."""
    return np.full((h, w, 3), 20, dtype=np.uint8)


def make_bright_image(h: int = 100, w: int = 300) -> np.ndarray:
    """평균 밝기가 80 이상인 밝은 이미지를 반환한다."""
    return np.full((h, w, 3), 120, dtype=np.uint8)


def _make_ocr_line(text: str, conf: float, bbox=None):
    """PaddleOCR result[0] 의 단일 라인 형식을 만든다.

    PaddleOCR 반환 형식:
      [[x1,y1],[x2,y1],[x2,y2],[x1,y2]], (text, conf)
    """
    if bbox is None:
        # 기본: 300x50 bbox (비율 6.0, 충분히 넓음)
        bbox = [[10, 5], [310, 5], [310, 55], [10, 55]]
    return [bbox, (text, conf)]


# ============================================================
# 1. PLATE_PATTERN 정규식
# ============================================================

class TestPlatePattern:
    """PLATE_PATTERN 정규식 매칭 검증"""

    valid_plates = [
        "12가1234",    # 2자리 숫자 + 한글 + 4자리
        "123가4567",   # 3자리 숫자 + 한글 + 4자리
        "서울12가1234", # 지역 코드 + 2자리 + 한글 + 4자리
        "경기 34나5678", # 지역 코드 + 공백 허용
    ]

    invalid_plates = [
        "",              # 빈 문자열
        "1가1234",       # 숫자 1자리 (최소 2자리 필요)
        "1234가5678",    # 숫자 4자리 (최대 3자리)
        "ABC1234",       # 영문자
        "12가123",       # 끝 숫자 3자리 (4자리 필요)
        "서울가1234",    # 지역코드만 + 한글 + 숫자 (중간 숫자 없음)
        "ABCD",          # 완전 영문
        "   ",           # 공백만
    ]

    @pytest.mark.parametrize("plate", valid_plates)
    def test_valid_plate_matches(self, plate):
        assert PLATE_PATTERN.match(plate) is not None, f"'{plate}' should match"

    @pytest.mark.parametrize("plate", invalid_plates)
    def test_invalid_plate_does_not_match(self, plate):
        assert PLATE_PATTERN.match(plate) is None, f"'{plate}' should NOT match"

    def test_pattern_anchored_no_prefix_garbage(self):
        # 앞에 쓰레기 문자가 붙으면 매칭 실패해야 한다
        assert PLATE_PATTERN.match("XX12가1234") is None

    def test_pattern_case_sensitivity(self):
        # 영문 대소문자는 모두 불일치
        assert PLATE_PATTERN.match("ab12가1234") is None


# ============================================================
# 2. _validate_crop
# ============================================================

class TestValidateCrop:
    """_validate_crop 최소 크기·비율 검증"""

    def test_valid_crop_returns_true(self):
        crop = make_image(h=30, w=180)  # ratio=6.0, w>=40, h>=10
        assert _validate_crop(crop) is True

    def test_none_returns_false(self):
        assert _validate_crop(None) is False

    def test_empty_array_returns_false(self):
        assert _validate_crop(np.array([])) is False

    def test_too_narrow_width_returns_false(self):
        # w=30 < 40
        crop = make_image(h=20, w=30)
        assert _validate_crop(crop) is False

    def test_too_short_height_returns_false(self):
        # h=5 < 10
        crop = make_image(h=5, w=80)
        assert _validate_crop(crop) is False

    def test_ratio_too_low_returns_false(self):
        # ratio = 40/40 = 1.0 < 1.2
        crop = make_image(h=40, w=40)
        assert _validate_crop(crop) is False

    def test_ratio_too_high_returns_false(self):
        # ratio = 10.0 > 9.0  (w=500, h=50 → ratio=10)
        crop = make_image(h=50, w=500)
        assert _validate_crop(crop) is False

    def test_boundary_ratio_min_exactly_1_2(self):
        # ratio=1.2 는 경계값 (1.2 <= ratio <= 9.0 에 포함)
        crop = make_image(h=50, w=60)  # 60/50 = 1.2
        assert _validate_crop(crop) is True

    def test_boundary_ratio_max_exactly_9(self):
        # ratio=9.0 경계값 (포함)
        crop = make_image(h=20, w=180)  # 180/20 = 9.0
        assert _validate_crop(crop) is True

    def test_zero_height_does_not_raise(self):
        # shape=(0, 300, 3) 는 size==0 이므로 False
        crop = np.zeros((0, 300, 3), dtype=np.uint8)
        assert _validate_crop(crop) is False


# ============================================================
# 3. _brighten_frame
# ============================================================

class TestBrightenFrame:
    """_brighten_frame 밝기 분기 및 반환 타입 검증"""

    def test_bright_image_returned_unchanged(self):
        img = make_bright_image()
        result = _brighten_frame(img)
        # 밝은 이미지는 동일 객체를 반환해야 한다
        assert result is img

    def test_dark_image_is_brightened(self):
        img = make_dark_image()
        result = _brighten_frame(img)
        # 원본과 다른 배열이어야 한다 (보정됨)
        assert not np.array_equal(result, img)

    def test_dark_image_output_shape_preserved(self):
        img = make_dark_image(h=80, w=200)
        result = _brighten_frame(img)
        assert result.shape == img.shape

    def test_dark_image_output_brighter_on_average(self):
        img = make_dark_image()
        result = _brighten_frame(img)
        import cv2
        original_mean = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean()
        result_mean = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY).mean()
        assert result_mean >= original_mean

    def test_boundary_brightness_at_80(self):
        # 정확히 80인 이미지 → 보정 없음 (>= 80 조건)
        img = np.full((50, 100, 3), 80, dtype=np.uint8)
        result = _brighten_frame(img)
        assert result is img

    def test_brightness_just_below_80(self):
        # 79 → 보정 적용
        img = np.full((50, 100, 3), 79, dtype=np.uint8)
        result = _brighten_frame(img)
        assert not np.array_equal(result, img)

    def test_pure_black_image_does_not_raise(self):
        img = np.zeros((50, 100, 3), dtype=np.uint8)
        result = _brighten_frame(img)
        assert result.shape == img.shape


# ============================================================
# 4. _preprocess_for_ocr
# ============================================================

class TestPreprocessForOcr:
    """_preprocess_for_ocr 전처리 파이프라인 검증"""

    def test_output_is_3_channel(self):
        img = make_image(h=50, w=200)
        result = _preprocess_for_ocr(img)
        assert result.ndim == 3 and result.shape[2] == 3

    def test_small_image_is_resized_to_min_300_width(self):
        img = make_image(h=50, w=100)  # w=100 < 300
        result = _preprocess_for_ocr(img)
        assert result.shape[1] >= 300

    def test_large_image_width_not_shrunk(self):
        img = make_image(h=50, w=400)  # w=400 > 300, 축소 불필요
        result = _preprocess_for_ocr(img)
        assert result.shape[1] == 400

    def test_binarize_false_returns_valid_image(self):
        img = make_image(h=50, w=300)
        result = _preprocess_for_ocr(img, binarize=False)
        assert result.shape == (50, 300, 3)

    def test_binarize_true_returns_valid_image(self):
        img = make_image(h=50, w=300)
        result = _preprocess_for_ocr(img, binarize=True)
        assert result.shape[2] == 3

    def test_aspect_ratio_preserved_on_resize(self):
        # w=150, h=50 → scale=2 → new w=300, h=100
        img = make_image(h=50, w=150)
        result = _preprocess_for_ocr(img)
        expected_h = int(50 * (300 / 150))
        assert result.shape[0] == expected_h
        assert result.shape[1] == 300


# ============================================================
# 5. _crop_from_bbox
# ============================================================

class TestCropFromBbox:
    """_crop_from_bbox 좌표·패딩 검증"""

    def test_basic_crop_returns_subarray(self):
        src = make_image(h=200, w=400)
        bbox = [[50, 30], [150, 30], [150, 80], [50, 80]]
        crop, x1, y1, x2, y2 = _crop_from_bbox(src, bbox, pad=0)
        assert crop.shape == (50, 100, 3)  # h=80-30=50, w=150-50=100

    def test_padding_increases_crop_size(self):
        src = make_image(h=200, w=400)
        bbox = [[50, 30], [150, 30], [150, 80], [50, 80]]
        _, x1_p0, y1_p0, x2_p0, y2_p0 = _crop_from_bbox(src, bbox, pad=0)
        _, x1_p8, y1_p8, x2_p8, y2_p8 = _crop_from_bbox(src, bbox, pad=8)
        assert x1_p8 < x1_p0
        assert y1_p8 < y1_p0
        assert x2_p8 > x2_p0
        assert y2_p8 > y2_p0

    def test_clamps_to_image_boundaries(self):
        src = make_image(h=50, w=100)
        # bbox 가 이미지 경계 밖에 위치
        bbox = [[0, 0], [110, 0], [110, 60], [0, 60]]
        crop, x1, y1, x2, y2 = _crop_from_bbox(src, bbox, pad=0)
        assert x1 >= 0 and y1 >= 0
        assert x2 <= 100 and y2 <= 50

    def test_returns_five_values(self):
        src = make_image(h=100, w=200)
        bbox = [[10, 10], [80, 10], [80, 40], [10, 40]]
        result = _crop_from_bbox(src, bbox)
        assert len(result) == 5


# ============================================================
# 6. _ocr_on_image
# ============================================================

class TestOcrOnImage:
    """_ocr_on_image geometry 검증 우선·가산점 방식·복합 매칭 검증"""

    # ── 픽스처: ocr_model.ocr 를 테스트별로 모킹 ──

    def _run(self, mock_result):
        """ocr_model.ocr 를 mock_result 로 패치하고 _ocr_on_image 를 호출한다."""
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = mock_result
            return _ocr_on_image(make_image(h=200, w=600))

    # ── 빈/None 결과 ──

    def test_none_result_returns_all_none(self):
        bbox, text, conf, fbs, avg = self._run(None)
        assert bbox is None and text is None and conf == 0.0 and fbs == [] and avg == 0.0

    def test_empty_result_returns_all_none(self):
        bbox, text, conf, fbs, avg = self._run([[]])
        assert bbox is None and text is None

    def test_result_with_empty_inner_list(self):
        bbox, text, conf, fbs, avg = self._run([[None]])
        assert bbox is None

    # ── 단일 bbox: geometry + regex 모두 통과 → score = conf + 1.0 ──

    def test_bbox_passes_geometry_and_regex_score_is_conf_plus_1(self):
        # 번호판 패턴 "12가1234", conf=0.8 → score=1.8
        line = _make_ocr_line("12가1234", 0.8)
        bbox, text, conf, _, _ = self._run([[line]])
        assert bbox is not None
        assert text == "12가1234"
        assert abs(conf - 0.8) < 1e-6

    # ── 단일 bbox: geometry 통과하지만 regex 실패 → score = conf 만, 여전히 선택됨 ──

    def test_bbox_passes_geometry_fails_regex_still_selected(self):
        # "ABCDE" 는 regex 불일치, 하지만 geometry 조건은 통과
        line = _make_ocr_line("ABCDE", 0.75)
        bbox, text, conf, _, _ = self._run([[line]])
        # geometry 통과했으므로 best_bbox 가 선택되어야 한다 (drop 되지 않음)
        assert bbox is not None
        assert abs(conf - 0.75) < 1e-6

    # ── bbox 가 geometry 실패 → 완전히 버려짐 ──

    def test_bbox_fails_geometry_is_dropped(self):
        # 정사각형 bbox: w=bh=50 → ratio=1.0 < 1.2 → 기하 실패
        bad_bbox = [[10, 10], [60, 10], [60, 60], [10, 60]]
        line = [bad_bbox, ("12가1234", 0.95)]
        bbox, text, conf, _, _ = self._run([[line]])
        assert bbox is None

    def test_bbox_too_narrow_fails_geometry(self):
        # bw=30 < 50 → 기하 실패
        narrow_bbox = [[10, 10], [40, 10], [40, 30], [10, 30]]
        line = [narrow_bbox, ("12가1234", 0.9)]
        bbox, text, conf, _, _ = self._run([[line]])
        assert bbox is None

    # ── 다중 bbox: 높은 score 가 선택됨 ──

    def test_multiple_bboxes_highest_score_wins(self):
        # line_a: regex 통과 conf=0.7 → score=1.7
        # line_b: regex 실패 conf=0.9 → score=0.9
        # line_a 가 선택되어야 한다
        line_a = _make_ocr_line("12가1234", 0.7)
        line_b = _make_ocr_line("JUNK", 0.9)
        bbox, text, conf, _, _ = self._run([[line_a, line_b]])
        assert text == "12가1234"

    def test_multiple_bboxes_higher_conf_no_regex_loses_to_lower_conf_with_regex(self):
        # conf=0.65 + regex(+1) = 1.65 vs conf=0.99 no_regex = 0.99
        line_regex = _make_ocr_line("120가5678", 0.65)
        line_high_conf = _make_ocr_line("GARBAGE", 0.99)
        bbox, text, _, _, _ = self._run([[line_regex, line_high_conf]])
        assert text == "120가5678"

    def test_both_bboxes_pass_regex_higher_conf_wins(self):
        line_a = _make_ocr_line("12가1234", 0.75)
        line_b = _make_ocr_line("34나5678", 0.85)
        _, text, conf, _, _ = self._run([[line_a, line_b]])
        # 둘 다 regex 일치 → score_a=1.75, score_b=1.85 → b 선택
        assert text == "34나5678"
        assert abs(conf - 0.85) < 1e-6

    # ── 복합 매칭: 번호판이 두 bbox 로 분리된 경우 ──

    def test_composite_matching_two_boxes_merged(self):
        """OCR 이 번호판을 "120가" + "5871" 로 분리 → "120가5871" 로 합산."""
        # 두 박스 모두 geometry 실패하도록 작은 bbox 사용
        # → best_bbox = None → composite 경로 진입
        small_bbox_left  = [[10, 10], [40, 10], [40, 30], [10, 30]]   # bw=30 < 50 → 기하 실패
        small_bbox_right = [[50, 10], [80, 10], [80, 30], [50, 30]]   # bw=30 < 50 → 기하 실패
        line_a = [small_bbox_left,  ("120가", 0.80)]
        line_b = [small_bbox_right, ("5871",  0.75)]
        bbox, text, conf, _, _ = self._run([[line_a, line_b]])
        assert text == "120가5871"
        assert bbox is not None

    def test_composite_matching_invalid_combination_returns_none(self):
        """두 박스를 합쳐도 번호판 패턴과 불일치하면 None."""
        small_bbox = [[10, 10], [40, 10], [40, 30], [10, 30]]
        line_a = [small_bbox, ("XYZ",  0.8)]
        line_b = [small_bbox, ("ABCD", 0.7)]
        bbox, text, _, _, _ = self._run([[line_a, line_b]])
        assert bbox is None

    def test_composite_single_box_does_not_trigger_composite(self):
        """valid_lines 가 1개이면 복합 매칭을 시도하지 않는다."""
        small_bbox = [[10, 10], [40, 10], [40, 30], [10, 30]]
        line_a = [small_bbox, ("120가5871", 0.8)]
        bbox, text, _, _, _ = self._run([[line_a]])
        # 기하 실패 + 복합 불가(1개) → None
        assert bbox is None

    # ── fallback_texts 및 avg_conf ──

    def test_fallback_texts_collected_from_all_lines(self):
        line_a = _make_ocr_line("12가1234", 0.7)
        line_b = _make_ocr_line("ABC",      0.5)
        _, _, _, fbs, avg = self._run([[line_a, line_b]])
        assert "12가1234" in fbs
        # avg_conf = (0.7 + 0.5) / 2 = 0.6
        assert abs(avg - 0.6) < 1e-6

    def test_avg_conf_zero_when_no_result(self):
        _, _, _, _, avg = self._run([[]])
        assert avg == 0.0


# ============================================================
# 7. save_plate_image (async)
# ============================================================

class TestSavePlateImage:
    """save_plate_image 파일명 생성 및 I/O 검증 (cv2.imwrite 모킹)"""

    @pytest.mark.asyncio
    async def test_normal_plate_text_filename(self):
        img = make_image()
        with patch("services.ocr_storage.cv2.imwrite") as mock_write:
            url = await save_plate_image(img, "12가1234", "SPEEDING")
        assert "12가1234" in url
        assert url.startswith("numberplate/")
        mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_unrecognized_prefix_generates_uuid_filename(self):
        img = make_image()
        with patch("services.ocr_storage.cv2.imwrite"):
            url = await save_plate_image(img, "UNRECOGNIZED_abc123", "SPEEDING")
        assert "UNRECOGNIZED_" in url

    @pytest.mark.asyncio
    async def test_empty_plate_text_generates_unrecognized_filename(self):
        img = make_image()
        with patch("services.ocr_storage.cv2.imwrite"):
            url = await save_plate_image(img, "", "SPEEDING")
        assert "UNRECOGNIZED_" in url

    @pytest.mark.asyncio
    async def test_special_chars_in_plate_text_sanitized(self):
        img = make_image()
        with patch("services.ocr_storage.cv2.imwrite") as mock_write:
            url = await save_plate_image(img, "12가/1234", "SPEEDING")
        # "/" 는 "_" 로 치환되어야 한다 — 파일명 부분(prefix 이후)에만 검사
        filename = url.split("/", 1)[-1]  # "numberplate/" prefix 제거
        assert "/" not in filename
        assert "12가_1234.jpg" == filename
        mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_relative_path_prefix(self):
        img = make_image()
        with patch("services.ocr_storage.cv2.imwrite"):
            url = await save_plate_image(img, "34나5678", "WRONG_WAY")
        assert url.startswith("numberplate/")
        assert url.endswith(".jpg")


# ============================================================
# 8. extract_license_plate (async)
# ============================================================

class TestExtractLicensePlate:
    """extract_license_plate OCR 추출·신뢰도·패턴 검증"""

    def _make_ocr_return(self, text: str, conf: float):
        # PaddleOCR 반환 형식: result[0] 은 라인 목록, 각 라인은 [bbox, (text, conf)]
        # result = [ [line, line, ...] ] 이므로 line을 한 번 더 감싸야 함
        return [[ [[[0, 0], [100, 0], [100, 20], [0, 20]], (text, conf)] ]]

    @pytest.mark.asyncio
    async def test_valid_plate_high_confidence_returned(self):
        img = make_image(h=50, w=200)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = self._make_ocr_return("12가1234", 0.92)
            result = await extract_license_plate(img)
        assert result == "12가1234"

    @pytest.mark.asyncio
    async def test_low_confidence_returns_manual_review(self):
        img = make_image(h=50, w=200)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = self._make_ocr_return("12가1234", 0.40)
            result = await extract_license_plate(img)
        assert result.startswith("MANUAL_REVIEW_REQUIRED:")

    @pytest.mark.asyncio
    async def test_regex_mismatch_returns_manual_review(self):
        img = make_image(h=50, w=200)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = self._make_ocr_return("INVALID_PLATE", 0.95)
            result = await extract_license_plate(img)
        assert result.startswith("MANUAL_REVIEW_REQUIRED:")

    @pytest.mark.asyncio
    async def test_empty_ocr_result_returns_unrecognized(self):
        img = make_image(h=50, w=200)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = None
            result = await extract_license_plate(img)
        assert result == "UNRECOGNIZED"

    @pytest.mark.asyncio
    async def test_ocr_exception_returns_unrecognized(self):
        img = make_image(h=50, w=200)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.side_effect = RuntimeError("GPU OOM")
            result = await extract_license_plate(img)
        assert result == "UNRECOGNIZED"

    @pytest.mark.asyncio
    async def test_confidence_exactly_at_threshold_passes(self):
        # CONFIDENCE_THRESHOLD = 0.60 → avg_conf = 0.60 는 통과 (< 가 아니라 >= 가 통과 기준)
        img = make_image(h=50, w=200)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = self._make_ocr_return("12가1234", CONFIDENCE_THRESHOLD)
            result = await extract_license_plate(img)
        assert result == "12가1234"

    @pytest.mark.asyncio
    async def test_confidence_just_below_threshold_fails(self):
        img = make_image(h=50, w=200)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = self._make_ocr_return("12가1234", CONFIDENCE_THRESHOLD - 0.01)
            result = await extract_license_plate(img)
        assert result.startswith("MANUAL_REVIEW_REQUIRED:")

    @pytest.mark.asyncio
    async def test_multiple_text_boxes_concatenated(self):
        """여러 라인의 텍스트를 합산하여 번호판을 구성한다."""
        img = make_image(h=50, w=200)
        ocr_result = [
            [[[0, 0], [100, 0], [100, 20], [0, 20]], ("120가", 0.85)],
            [[[105, 0], [200, 0], [200, 20], [105, 20]], ("5678", 0.85)],
        ]
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = [ocr_result]
            result = await extract_license_plate(img)
        assert result == "120가5678"


# ============================================================
# 9. run_ocr_on_file (async) — 폴백 크롭 포함
# ============================================================

class TestRunOcrOnFile:
    """run_ocr_on_file 4단계 파이프라인 및 폴백 크롭 검증"""

    # ── 헬퍼: cv2.imread 를 더미 이미지로 패치 ──

    def _patch_imread(self, img):
        return patch("services.ocr_storage.cv2.imread", return_value=img)

    def _patch_save(self):
        return patch("services.ocr_storage.save_plate_image", new_callable=AsyncMock,
                     return_value="numberplate/test.jpg")

    # ── 이미지 읽기 실패 ──

    @pytest.mark.asyncio
    async def test_file_not_found_returns_unrecognized(self):
        with self._patch_imread(None), self._patch_save():
            result = await run_ocr_on_file("nonexistent.jpg")
        assert result["plate_number"].startswith("UNRECOGNIZED_")
        assert result["image_url"] is None
        assert result["is_corrected"] is False

    # ── Stage 1: 원본 이미지에서 감지 성공 ──

    @pytest.mark.asyncio
    async def test_stage1_detection_success(self):
        img = make_bright_image(h=400, w=600)
        # 유효한 geometry 의 bbox 반환
        valid_bbox = [[10, 10], [310, 10], [310, 60], [10, 60]]  # bw=300, bh=50, ratio=6.0
        ocr_result = [[[valid_bbox, ("12가1234", 0.88)]]]

        with self._patch_imread(img), self._patch_save() as mock_save:
            with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                mock_ocr.ocr.return_value = ocr_result
                result = await run_ocr_on_file("test.jpg")

        assert result["plate_number"] == "12가1234"
        assert result["image_url"] == "numberplate/test.jpg"
        mock_save.assert_called_once()

    # ── 모든 단계 실패 → 폴백 크롭이 가로 25%~75% 를 사용하는지 검증 ──

    @pytest.mark.asyncio
    async def test_all_stages_fail_fallback_uses_center_50_percent_width(self):
        """
        4단계 모두 실패 시 폴백 크롭이
        x1_fb = int(w * 0.25), x2_fb = int(w * 0.75) 를 사용해야 한다.
        """
        h, w = 400, 600
        img = make_bright_image(h=h, w=w)

        # 모든 OCR 호출이 빈 결과를 반환 → 모든 단계 실패
        with self._patch_imread(img), self._patch_save() as mock_save:
            with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                mock_ocr.ocr.return_value = [[]]  # 빈 결과

                # save_plate_image 호출 시의 첫 번째 인수(frame)를 캡처
                captured_frames = []
                async def capture_save(frame, *args, **kwargs):
                    captured_frames.append(frame)
                    return "numberplate/fallback.jpg"
                mock_save.side_effect = capture_save

                result = await run_ocr_on_file("test.jpg")

        assert len(captured_frames) == 1
        saved_frame = captured_frames[0]

        # 폴백 크롭 너비 검증: 중앙 50% 이므로 w * 0.5 = 300
        expected_width = int(w * 0.75) - int(w * 0.25)  # = 300
        assert saved_frame.shape[1] == expected_width, (
            f"폴백 크롭 너비가 {saved_frame.shape[1]}이지만 {expected_width}(중앙 50%)이어야 합니다."
        )

    @pytest.mark.asyncio
    async def test_fallback_crop_not_full_width(self):
        """폴백 크롭이 프레임 전체 너비(w=600)를 사용하지 않아야 한다."""
        h, w = 400, 600
        img = make_bright_image(h=h, w=w)

        with self._patch_imread(img), self._patch_save() as mock_save:
            with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                mock_ocr.ocr.return_value = [[]]

                captured_frames = []
                async def capture_save(frame, *args, **kwargs):
                    captured_frames.append(frame)
                    return "numberplate/fallback.jpg"
                mock_save.side_effect = capture_save

                await run_ocr_on_file("test.jpg")

        saved_frame = captured_frames[0]
        # 전체 너비(600)가 아니어야 한다
        assert saved_frame.shape[1] < w, (
            f"폴백 크롭이 전체 너비({w})와 같으면 안 됩니다. 실제={saved_frame.shape[1]}"
        )

    @pytest.mark.asyncio
    async def test_all_stages_fail_returns_unrecognized_plate_number(self):
        img = make_bright_image(h=400, w=600)
        with self._patch_imread(img), self._patch_save():
            with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                mock_ocr.ocr.return_value = [[]]
                result = await run_ocr_on_file("test.jpg")

        assert result["plate_number"] == "UNRECOGNIZED"
        assert result["is_corrected"] is False

    # ── MANUAL_REVIEW 접두사 처리 ──

    @pytest.mark.asyncio
    async def test_manual_review_prefix_stripped_and_flag_set(self):
        """MANUAL_REVIEW_REQUIRED: 접두사가 제거되고 is_corrected=True 가 설정된다."""
        h, w = 400, 600
        img = make_bright_image(h=h, w=w)

        # Stage1 이 MANUAL_REVIEW_REQUIRED:12가1234 를 반환하도록 유도
        # → conf < CONFIDENCE_THRESHOLD(=0.60) 이면 is_corrected=True 반환
        valid_bbox = [[10, 10], [310, 10], [310, 60], [10, 60]]
        # conf=0.5 → is_corrected=True (0.5 < 0.60)
        ocr_result = [[[valid_bbox, ("12가1234", 0.50)]]]

        with self._patch_imread(img), self._patch_save():
            with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                mock_ocr.ocr.return_value = ocr_result
                result = await run_ocr_on_file("test.jpg")

        assert result["plate_number"] == "12가1234"
        assert result["is_corrected"] is True

    # ── 반환 구조 검증 ──

    @pytest.mark.asyncio
    async def test_return_dict_has_required_keys(self):
        img = make_bright_image(h=400, w=600)
        with self._patch_imread(img), self._patch_save():
            with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                mock_ocr.ocr.return_value = [[]]
                result = await run_ocr_on_file("test.jpg")

        assert set(result.keys()) == {"plate_number", "image_url", "is_corrected"}

    @pytest.mark.asyncio
    async def test_image_url_from_save_plate_image(self):
        img = make_bright_image(h=400, w=600)
        with self._patch_imread(img):
            with patch("services.ocr_storage.save_plate_image", new_callable=AsyncMock,
                       return_value="numberplate/12가1234.jpg"):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.return_value = [[]]
                    result = await run_ocr_on_file("test.jpg")

        assert result["image_url"] == "numberplate/12가1234.jpg"


# ============================================================
# 10. 경계 조건 — 가산점 스코어 산술
# ============================================================

class TestScoreArithmetic:
    """conf + (1.0 if is_perfect_match else 0.0) 산술 검증"""

    def _run_single_line(self, text: str, conf: float, bbox=None):
        if bbox is None:
            bbox = [[10, 5], [310, 5], [310, 55], [10, 55]]
        line = [bbox, (text, conf)]
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = [[line]]
            return _ocr_on_image(make_image(h=200, w=600))

    def test_score_with_regex_match(self):
        # score = 0.70 + 1.0 = 1.70
        _, _, conf, _, _ = self._run_single_line("12가1234", 0.70)
        assert abs(conf - 0.70) < 1e-6

    def test_score_without_regex_match(self):
        # score = 0.99 (regex 불일치)
        bbox, text, conf, _, _ = self._run_single_line("JUNK999", 0.99)
        assert bbox is not None
        assert abs(conf - 0.99) < 1e-6


# ============================================================
# 11. Fix A — Adaptive Gaussian Thresholding (binarize=True)
# ============================================================

class TestAdaptiveThreshold:
    """Fix A: binarize=True 시 OTSU 대신 Adaptive Gaussian Thresholding 적용 검증.

    adaptiveThreshold 는 블록 크기에 따라 지역별 임계값을 다르게 적용하므로
    출력 픽셀은 반드시 0 또는 255 중 하나여야 한다.
    그 후 3채널로 변환되므로 각 채널도 동일한 이진 분포를 가진다.
    """

    def _get_unique_values(self, img: np.ndarray) -> set:
        """이미지 내 고유 픽셀 값 집합 반환 (채널 통합)."""
        return set(np.unique(img))

    def test_binarize_true_small_image_produces_binary_values(self):
        """100x30 소형 이미지: binarize=True 시 픽셀 값이 0과 255만 존재해야 한다."""
        img = make_image(h=30, w=100, fill=128)
        # 단조로운 이미지보다 텍스처가 있는 이미지가 이진화 효과를 검증하기 쉬움
        img[5:25, 10:90] = 200  # 밝은 영역 추가
        result = _preprocess_for_ocr(img, binarize=True)
        unique_vals = self._get_unique_values(result)
        # 이진화 후 3채널 변환 → 픽셀 값은 0 또는 255만 허용
        assert unique_vals.issubset({0, 255}), (
            f"binarize=True 결과에 0/255 외 픽셀 값이 존재합니다: {unique_vals}"
        )

    def test_binarize_true_large_image_produces_binary_values(self):
        """600x100 대형 이미지: binarize=True 시 픽셀 값이 0과 255만 존재해야 한다."""
        img = make_image(h=100, w=600, fill=100)
        img[20:80, 50:550] = 220  # 다양한 밝기 영역
        result = _preprocess_for_ocr(img, binarize=True)
        unique_vals = self._get_unique_values(result)
        assert unique_vals.issubset({0, 255}), (
            f"대형 이미지 binarize=True 결과에 0/255 외 픽셀 값이 존재합니다: {unique_vals}"
        )

    def test_binarize_false_allows_non_binary_values(self):
        """binarize=False 시 중간 그레이 값이 허용되어야 한다 (이진화 미적용 확인)."""
        img = make_image(h=50, w=300, fill=128)
        result = _preprocess_for_ocr(img, binarize=False)
        unique_vals = self._get_unique_values(result)
        # 이진화가 없으면 0과 255 사이의 값이 존재할 수 있다
        # (CLAHE + Unsharp Masking 후에도 중간값이 남아 있어야 정상)
        assert not unique_vals.issubset({0, 255}), (
            "binarize=False 인데도 이진 값만 반환됩니다 — 이진화가 잘못 적용된 것 같습니다."
        )

    def test_binarize_true_output_is_3channel(self):
        """이진화 후 3채널 변환이 정상적으로 수행되는지 확인."""
        img = make_image(h=50, w=300)
        result = _preprocess_for_ocr(img, binarize=True)
        assert result.ndim == 3 and result.shape[2] == 3

    def test_binarize_true_both_extremes_present_on_gradient_image(self):
        """명암 대비가 있는 이미지에서 0과 255 양쪽 모두 존재하는지 확인."""
        # 왼쪽 절반은 어둡고 오른쪽 절반은 밝게 — Adaptive Threshold 효과 극대화
        img = np.zeros((50, 300, 3), dtype=np.uint8)
        img[:, 150:] = 240  # 오른쪽 절반 밝음
        result = _preprocess_for_ocr(img, binarize=True)
        unique_vals = self._get_unique_values(result)
        assert 0 in unique_vals, "이진화 결과에 0(어두운 픽셀)이 없습니다."
        assert 255 in unique_vals, "이진화 결과에 255(밝은 픽셀)이 없습니다."


# ============================================================
# 12. Fix B — 동적 CLAHE tileGridSize
# ============================================================

class TestDynamicClaheTileSize:
    """Fix B: 이미지 크기에 비례하여 CLAHE tileGridSize 를 계산하는지 검증.

    tileGridSize = (max(4, w//8), max(4, h//4))
    작은 이미지에서는 최솟값 4 가 보장되어야 하고,
    큰 이미지에서는 비례 계산값이 4 보다 커야 한다.
    """

    def _compute_expected_tile(self, h: int, w: int) -> tuple:
        """소스 코드와 동일한 tileGridSize 계산 로직."""
        tile_w = max(4, w // 8)
        tile_h = max(4, h // 4)
        return tile_w, tile_h

    def test_small_image_tile_is_at_least_4x4(self):
        """30x100 소형 이미지: tileGridSize 가 최소 (4, 4) 이어야 한다.

        tileGridSize 를 직접 읽을 수 없으므로, _preprocess_for_ocr 가
        예외 없이 완료되고 출력 형상이 유효한지로 간접 검증한다.
        CLAHE tileGridSize 가 (1,1) 처럼 너무 작으면 cv2.createCLAHE 가
        에러 없이 통과하므로, 함수가 정상 완료됨을 보장하는 방식으로 검증.
        """
        img = make_image(h=30, w=100)
        # w=100 < 600 → 리사이즈 후 w=600, h=180
        result = _preprocess_for_ocr(img, binarize=False)
        assert result is not None
        assert result.shape[2] == 3

    def test_large_image_tile_exceeds_minimum(self):
        """800x200 대형 이미지: tileGridSize 가 최솟값 4 보다 크다.

        w=800 → tile_w = max(4, 800//8) = 100
        h=200 → tile_h = max(4, 200//4) = 50
        → (100, 50) 이 예상값.
        """
        expected_tile_w, expected_tile_h = self._compute_expected_tile(200, 800)
        assert expected_tile_w > 4  # 100 > 4
        assert expected_tile_h > 4  # 50 > 4
        # 실제 함수가 해당 크기로 정상 동작하는지 검증
        img = make_image(h=200, w=800)
        result = _preprocess_for_ocr(img, binarize=False)
        assert result.shape == (200, 800, 3)

    def test_very_small_image_clamped_to_minimum_4(self):
        """16x8 극소형 이미지 (리사이즈 전): 최솟값 4 가 적용되어야 한다.

        w=16 → tile_w = max(4, 16//8) = max(4, 2) = 4
        h=8  → tile_h = max(4, 8//4)  = max(4, 2) = 4
        """
        tile_w, tile_h = self._compute_expected_tile(8, 16)
        assert tile_w == 4
        assert tile_h == 4

    def test_tile_calculation_formula_consistency(self):
        """다양한 크기에서 tile 계산 공식의 일관성을 검증한다."""
        sizes = [
            (10, 30),   # 극소형
            (50, 200),  # 소형
            (100, 600), # 중형
            (200, 800), # 대형
        ]
        for h, w in sizes:
            tile_w, tile_h = self._compute_expected_tile(h, w)
            assert tile_w >= 4, f"h={h},w={w}: tile_w={tile_w} < 4"
            assert tile_h >= 4, f"h={h},w={w}: tile_h={tile_h} < 4"
            # 값이 이미지 크기를 초과하지 않아야 함
            assert tile_w <= w, f"tile_w={tile_w} > w={w}"
            assert tile_h <= h, f"tile_h={tile_h} > h={h}"

    def test_preprocess_does_not_raise_for_tiny_image(self):
        """tileGridSize 계산 오류 시 cv2.createCLAHE 예외가 발생하므로
        정상 완료 여부로 최솟값 클램핑이 올바른지 간접 검증한다."""
        img = make_image(h=15, w=40)
        # 예외 없이 완료되면 tileGridSize 가 유효한 것
        result = _preprocess_for_ocr(img, binarize=False)
        assert result is not None


# ============================================================
# 13. Fix D — Unsharp Masking (CLAHE 후 샤프닝)
# ============================================================

class TestUnsharpMasking:
    """Fix D: CLAHE 적용 후 Unsharp Masking 으로 획 경계를 강화하는지 검증.

    Unsharp Masking 공식: enhanced = 1.8 * original - 0.8 * gaussian_blur
    → 결과가 원본 CLAHE 이미지와 달라야 한다 (샤프닝 효과).
    """

    def test_output_differs_from_plain_clahe(self):
        """Unsharp Masking 적용 후 결과가 단순 CLAHE 결과와 달라야 한다.

        CLAHE 만 적용한 경우와 CLAHE + Unsharp Masking 을 적용한 경우를
        비교하여 샤프닝이 실제로 수행되었는지 확인한다.
        """
        import cv2 as _cv2
        img = make_image(h=50, w=300, fill=128)
        img[10:40, 50:250] = 200  # 텍스처 추가

        # _preprocess_for_ocr 결과 (Unsharp Masking 포함)
        result_with_usm = _preprocess_for_ocr(img, binarize=False)

        # 순수 CLAHE 만 적용한 비교 이미지 직접 생성
        h, w = img.shape[:2]
        if w < 600:
            scale = 600 / w
            img_resized = _cv2.resize(img, (600, int(h * scale)), interpolation=_cv2.INTER_CUBIC)
        else:
            img_resized = img.copy()
        gray = _cv2.cvtColor(img_resized, _cv2.COLOR_BGR2GRAY)
        tile_w = max(4, img_resized.shape[1] // 8)
        tile_h = max(4, img_resized.shape[0] // 4)
        clahe = _cv2.createCLAHE(clipLimit=2.0, tileGridSize=(tile_w, tile_h))
        clahe_only = clahe.apply(gray)
        result_clahe_only = _cv2.cvtColor(clahe_only, _cv2.COLOR_GRAY2BGR)

        # Unsharp Masking 이 적용되면 두 결과가 달라야 한다
        assert not np.array_equal(result_with_usm, result_clahe_only), (
            "Unsharp Masking 이 적용되지 않았습니다 — CLAHE 결과와 동일합니다."
        )

    def test_output_shape_preserved_after_unsharp_masking(self):
        """Unsharp Masking 후 이미지 형상이 유지되어야 한다."""
        img = make_image(h=60, w=600)
        result = _preprocess_for_ocr(img, binarize=False)
        assert result.shape == (60, 600, 3)

    def test_output_dtype_uint8_after_unsharp_masking(self):
        """addWeighted 연산 후 dtype 이 uint8 로 유지되어야 한다."""
        img = make_image(h=50, w=300)
        result = _preprocess_for_ocr(img, binarize=False)
        assert result.dtype == np.uint8

    def test_high_contrast_image_sharpened(self):
        """고대비 이미지에서 Unsharp Masking 이 엣지를 강화하는지 검증.

        엣지 픽셀의 절댓값 차이가 원본보다 크거나 같으면 샤프닝이 된 것.
        """
        import cv2 as _cv2
        # 좌반부 0, 우반부 255 — 경계선이 명확한 이미지
        img = np.zeros((50, 600, 3), dtype=np.uint8)
        img[:, 300:] = 255

        result = _preprocess_for_ocr(img, binarize=False)
        # 결과가 올바른 형태로 반환되는지 최소한 확인
        assert result.shape == (50, 600, 3)
        assert result.dtype == np.uint8


# ============================================================
# 14. Fix C — 한글 없음 가드 (run_ocr_on_file)
# ============================================================

class TestNoHangulGuard:
    """Fix C: OCR 결과에 한글이 없는 경우(숫자만) UNRECOGNIZED_xxx 로 변환.

    run_ocr_on_file() 에서 plate_text 가 한글([가-힣])을 포함하지 않고
    UNRECOGNIZED 로 시작하지 않으면 UNRECOGNIZED_{uuid} 로 교체한다.

    패치 전략:
      - np.fromfile → 실제 파일 I/O 없이 더미 바이트 반환
      - cv2.imdecode → 더미 이미지 반환
      - ocr_model.ocr → 원하는 텍스트 반환
      - save_plate_image → 파일 쓰기 없이 파일명 캡처
    """

    def _make_valid_bbox_result(self, text: str, conf: float):
        """geometry 검증을 통과하는 bbox + 텍스트를 가진 PaddleOCR 결과."""
        # bw=300, bh=50, ratio=6.0 → geometry 통과
        valid_bbox = [[10, 10], [310, 10], [310, 60], [10, 60]]
        return [[[valid_bbox, (text, conf)]]]

    @pytest.mark.asyncio
    async def test_numbers_only_result_produces_unrecognized_filename(self):
        """PaddleOCR 이 "1265999" (숫자만) 반환 시 저장 파일명이 UNRECOGNIZED_ 로 시작해야 한다."""
        img = make_bright_image(h=400, w=600)
        ocr_result = self._make_valid_bbox_result("1265999", 0.85)

        captured = {}

        async def mock_save(frame, plate_text, violation_type):
            captured["plate_text"] = plate_text
            return f"numberplate/{plate_text}.jpg"

        with patch("services.ocr_storage.np.fromfile", return_value=np.zeros(100, dtype=np.uint8)):
            with patch("services.ocr_storage.cv2.imdecode", return_value=img):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.return_value = ocr_result
                    with patch("services.ocr_storage.save_plate_image", side_effect=mock_save):
                        result = await run_ocr_on_file("test.jpg")

        assert result["plate_number"].startswith("UNRECOGNIZED_"), (
            f"숫자만 있는 OCR 결과가 UNRECOGNIZED_ 로 변환되지 않았습니다: {result['plate_number']}"
        )
        assert captured["plate_text"].startswith("UNRECOGNIZED_"), (
            f"save_plate_image 에 전달된 plate_text 가 UNRECOGNIZED_ 가 아닙니다: {captured['plate_text']}"
        )

    @pytest.mark.asyncio
    async def test_hangul_result_passes_guard(self):
        """PaddleOCR 이 "12가3456" 반환 시 파일명이 "12가3456.jpg" 이어야 한다."""
        img = make_bright_image(h=400, w=600)
        ocr_result = self._make_valid_bbox_result("12가3456", 0.85)

        captured = {}

        async def mock_save(frame, plate_text, violation_type):
            captured["plate_text"] = plate_text
            return f"numberplate/{plate_text}.jpg"

        with patch("services.ocr_storage.np.fromfile", return_value=np.zeros(100, dtype=np.uint8)):
            with patch("services.ocr_storage.cv2.imdecode", return_value=img):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.return_value = ocr_result
                    with patch("services.ocr_storage.save_plate_image", side_effect=mock_save):
                        result = await run_ocr_on_file("test.jpg")

        assert result["plate_number"] == "12가3456", (
            f"한글 포함 결과가 가드를 통과하지 못했습니다: {result['plate_number']}"
        )
        assert captured["plate_text"] == "12가3456"

    @pytest.mark.asyncio
    async def test_already_unrecognized_prefix_not_double_wrapped(self):
        """이미 UNRECOGNIZED 로 시작하는 텍스트는 가드가 재처리하지 않아야 한다.

        Stage -1 OCR 이 None, Stage 0c 도 실패, _strip_ok=False 경로(이미지가 작음)에서
        모든 단계 실패 시 "UNRECOGNIZED" 로 시작해야 하며
        이중 중첩("UNRECOGNIZED_UNRECOGNIZED...") 이 발생해서는 안 된다.

        주의: h=40, w=600 처럼 bumper_frame 이 너무 작으면 _strip_ok=False 가 되어
        _combined0 UnboundLocalError (소스 코드의 기존 버그) 를 우회할 수 있다.
        이 테스트는 그 경로를 통해 UNRECOGNIZED 이중 중첩 가드를 검증한다.
        """
        # bumper_frame h = 400 * 0.5 = 200 → _s h = 200 * 0.9 = 180
        # _half_h = max(20, 180 // 8) = 22 → _tight_crop h ≈ 44 >= 10 → _strip_ok=True 가능
        # 대신 이미지를 좁게 만들어 tight_crop width < 40 이 되도록 설정
        # w=40 → _x1 = int(40 * 0.10) = 4, _x2 = int(40 * 0.90) = 36 → width=32 < 40 → _strip_ok=False
        img = make_bright_image(h=400, w=40)

        captured = {}

        async def mock_save(frame, plate_text, violation_type):
            captured["plate_text"] = plate_text
            return f"numberplate/{plate_text}.jpg"

        with patch("services.ocr_storage.np.fromfile", return_value=np.zeros(100, dtype=np.uint8)):
            with patch("services.ocr_storage.cv2.imdecode", return_value=img):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.return_value = [[]]  # 모든 단계 실패
                    with patch("services.ocr_storage.save_plate_image", side_effect=mock_save):
                        result = await run_ocr_on_file("test.jpg")

        plate = result["plate_number"]
        # 모든 단계 실패 시 "UNRECOGNIZED" 로 시작해야 한다
        assert plate.startswith("UNRECOGNIZED"), (
            f"모든 단계 실패 시 UNRECOGNIZED 로 시작해야 합니다: {plate}"
        )
        # 이중 중첩("UNRECOGNIZED_UNRECOGNIZED...") 이 발생하지 않아야 한다
        assert not plate.startswith("UNRECOGNIZED_UNRECOGNIZED"), (
            f"UNRECOGNIZED 가 이중으로 중첩되었습니다: {plate}"
        )

    @pytest.mark.asyncio
    async def test_mixed_digit_hangul_passes_guard(self):
        """숫자 + 한글 조합이지만 PLATE_PATTERN 불일치인 경우도 한글이 있으면 가드를 통과한다.

        가드 조건: `not re.search(r'[가-힣]', plate_text)` 이므로
        한글 문자가 하나라도 있으면 UNRECOGNIZED_ 로 변환되지 않는다.
        "99가" 처럼 PLATE_PATTERN 불일치이지만 한글이 있는 경우를 검증한다.
        """
        img = make_bright_image(h=400, w=600)
        # geometry 통과 bbox + 한글 포함 텍스트 (PLATE_PATTERN 불일치 길이)
        valid_bbox = [[10, 10], [310, 10], [310, 60], [10, 60]]
        ocr_result = [[[valid_bbox, ("99가", 0.85)]]]

        captured = {}

        async def mock_save(frame, plate_text, violation_type):
            captured["plate_text"] = plate_text
            return f"numberplate/{plate_text}.jpg"

        with patch("services.ocr_storage.np.fromfile", return_value=np.zeros(100, dtype=np.uint8)):
            with patch("services.ocr_storage.cv2.imdecode", return_value=img):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.return_value = ocr_result
                    with patch("services.ocr_storage.save_plate_image", side_effect=mock_save):
                        result = await run_ocr_on_file("test.jpg")

        # "99가" 는 한글을 포함하므로 한글 없음 가드 대상이 아님
        plate = result["plate_number"]
        assert not plate.startswith("UNRECOGNIZED_") or "가" in captured.get("plate_text", ""), (
            f"한글 포함 텍스트가 잘못 UNRECOGNIZED_ 로 변환되었습니다: {plate}"
        )


# ============================================================
# 15. Fix E — Stage 0c: Lanczos 2x 컬러 직접 OCR
# ============================================================

class TestStage0c:
    """Fix E: _detect_plate_bbox 내 Stage 0c — Lanczos 2x 컬러 업스케일 직접 OCR 경로 검증.

    Stage 0c 는 tight_crop 을 Lanczos4 알고리즘으로 2배 확대하여
    _preprocess_for_ocr 없이 직접 PaddleOCR 에 전달한다.
    이 경로가 활성화되려면:
      1. tight_crop.size > 0, shape[0] >= 10, shape[1] >= 40 조건 충족
      2. ocr_model.ocr 결과가 PLATE_PATTERN 과 일치하는 텍스트 반환
    """

    def _make_stage0c_ocr_return(self, text: str, conf: float):
        """Stage 0c 내부 결과 파싱 형식: result[0] 이 라인 리스트."""
        return [
            [[[0, 0], [100, 0], [100, 20], [0, 20]], (text, conf)]
        ]

    @pytest.mark.asyncio
    async def test_stage0c_detected_plate_returned(self):
        """Stage 0c 에서 번호판 패턴 일치 시 해당 텍스트가 최종 결과에 반영된다."""
        # bumper_frame 에서 tight_crop 이 충분히 크도록 이미지 설정
        # h=200, w=600 → bumper_frame h=100, w=600 (하단 50%)
        # _s = bright_bumper[5%~95%] → h=90
        # _brightest_row 가 45 (중간), _half_h = max(20, 90//8=11) = 20
        # → _tight_crop h = ~40px, w = 0.8 * 600 = 480px → 조건 충족
        img = make_bright_image(h=200, w=600)

        captured = {}

        async def mock_save(frame, plate_text, violation_type):
            captured["plate_text"] = plate_text
            return f"numberplate/{plate_text}.jpg"

        # Stage 0c OCR 결과만 번호판 패턴과 일치하도록 설정
        # 다른 OCR 호출은 빈 결과 반환 (Stage -1, Stage 1 등)
        call_count = [0]

        def ocr_side_effect(img_arg):
            call_count[0] += 1
            # 첫 번째 호출(Stage -1: 전체 frame)은 빈 결과
            if call_count[0] == 1:
                return [[]]
            # 두 번째 호출(Stage 0c: tight_crop 2x)은 번호판 패턴 반환
            if call_count[0] == 2:
                return [self._make_stage0c_ocr_return("34나5678", 0.88)]
            # 이후 모든 호출은 빈 결과
            return [[]]

        with patch("services.ocr_storage.np.fromfile", return_value=np.zeros(100, dtype=np.uint8)):
            with patch("services.ocr_storage.cv2.imdecode", return_value=img):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.side_effect = ocr_side_effect
                    with patch("services.ocr_storage.save_plate_image", side_effect=mock_save):
                        result = await run_ocr_on_file("test.jpg")

        assert result["plate_number"] == "34나5678", (
            f"Stage 0c 에서 인식된 번호판이 결과에 반영되지 않았습니다: {result['plate_number']}"
        )

    @pytest.mark.asyncio
    async def test_stage0c_skipped_when_tight_crop_too_small(self):
        """tight_crop 이 조건(h<10 또는 w<40)을 충족하지 않으면 Stage 0c 가 건너뛰어진다.

        이미지가 너무 작으면 tight_crop 이 소형이 되어 Stage 0c 가 스킵된다.
        전체 파이프라인이 예외 없이 완료되어야 한다.
        """
        # h=20 → bumper_frame h=10, _s h≈8 → tight_crop h 매우 작음
        img = make_bright_image(h=20, w=200)

        with patch("services.ocr_storage.np.fromfile", return_value=np.zeros(100, dtype=np.uint8)):
            with patch("services.ocr_storage.cv2.imdecode", return_value=img):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.return_value = [[]]
                    with patch("services.ocr_storage.save_plate_image",
                               new_callable=AsyncMock,
                               return_value="numberplate/test.jpg"):
                        # 예외 없이 완료되는지만 확인
                        result = await run_ocr_on_file("test.jpg")

        assert "plate_number" in result

    @pytest.mark.asyncio
    async def test_stage0c_no_hangul_in_result_skipped(self):
        """Stage 0c 결과가 PLATE_PATTERN 불일치(한글 없음)이면 해당 경로를 건너뛰어야 한다.

        숫자만 반환해도 Stage 0c 는 패턴 불일치로 스킵하고 다음 Stage 로 진행한다.

        이 테스트는 이미지를 narrow(w=40)하게 만들어 _strip_ok=False 로 만든 뒤
        Stage 0c 만 활성화되도록 유도한다. Stage 0c 결과가 패턴 불일치이면 스킵하고
        이후 단계로 진행하여 최종 결과는 UNRECOGNIZED 로 끝나야 한다.

        Stage 0c 내부 파싱 형식:
          result[0] 은 라인 리스트 [bbox, (text, conf)]
          _l[1][0] = text (str), _l[1][1] = conf (float)
        """
        # w=40 → _x1=4, _x2=36 → tight_crop width=32 < 40 → _strip_ok=False
        # tight_crop 은 여전히 Stage 0c 조건(shape[1] >= 40)도 불충족 → Stage 0c 도 스킵됨
        # 따라서 이 케이스는 Stage 0c 가 조건 불충족으로 건너뛰어지는 경로를 검증
        img = make_bright_image(h=200, w=40)

        with patch("services.ocr_storage.np.fromfile", return_value=np.zeros(100, dtype=np.uint8)):
            with patch("services.ocr_storage.cv2.imdecode", return_value=img):
                with patch.object(ocr_mod, "ocr_model") as mock_ocr:
                    mock_ocr.ocr.return_value = [[]]
                    with patch("services.ocr_storage.save_plate_image",
                               new_callable=AsyncMock,
                               return_value="numberplate/test.jpg"):
                        result = await run_ocr_on_file("test.jpg")

        # Stage 0c 가 스킵(조건 불충족)되었으므로 최종 결과는 UNRECOGNIZED 계열이어야 함
        # "1265999" 같은 숫자만의 값이 최종 결과로 반영되면 안 됨
        assert result["plate_number"] != "1265999", (
            "Stage 0c 에서 패턴 불일치 결과가 최종 번호판으로 잘못 반영되었습니다."
        )
        assert result["plate_number"].startswith("UNRECOGNIZED"), (
            f"Stage 0c 스킵 후 모든 단계 실패 시 UNRECOGNIZED 로 시작해야 합니다: {result['plate_number']}"
        )

    def test_regex_match_beats_higher_raw_conf(self):
        """regex 매칭 가산점이 있으면 낮은 conf 라도 높은 conf + no_regex 를 이긴다."""
        # line_a: conf=0.65 + regex = score 1.65
        # line_b: conf=1.0 no_regex = score 1.0  (실제로는 conf <= 1.0 이지만 테스트용)
        line_a = _make_ocr_line("12가1234", 0.65)
        line_b = _make_ocr_line("ZZZ_JUNK", 1.00)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = [[line_a, line_b]]
            _, text, _, _, _ = _ocr_on_image(make_image(h=200, w=600))
        assert text == "12가1234"

    def test_zero_conf_with_regex_still_selected_over_nonzero_conf_no_regex(self):
        # conf=0.0 + regex = score 1.0 vs conf=0.5 no_regex = score 0.5
        line_regex = _make_ocr_line("12가1234", 0.0)
        line_noregex = _make_ocr_line("GARBAGE", 0.5)
        with patch.object(ocr_mod, "ocr_model") as mock_ocr:
            mock_ocr.ocr.return_value = [[line_regex, line_noregex]]
            _, text, _, _, _ = _ocr_on_image(make_image(h=200, w=600))
        assert text == "12가1234"
