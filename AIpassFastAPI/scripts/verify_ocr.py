"""
OCR 인식률 배치 검증 스크립트
data/carnumber/ 전체 이미지에 대해 run_ocr_on_file을 실행하고 결과를 확인한다.

실행:
  cd AIpassFastAPI
  python scripts/verify_ocr.py                      # 전체 실행
  python scripts/verify_ocr.py --limit 10           # 처음 10개만
  python scripts/verify_ocr.py --filter 120가5871   # 특정 파일명 포함
  python scripts/verify_ocr.py --fail-only          # FAIL/REVIEW만 출력
"""
import asyncio
import logging
import os
import sys
import time
import argparse
import re
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CARNUMBER_DIR = Path("data/carnumber")

PASS_STR = "\033[92mPASS\033[0m"
FAIL_STR = "\033[91mFAIL\033[0m"
WARN_STR = "\033[93mREVIEW\033[0m"


def parse_args():
    parser = argparse.ArgumentParser(description="OCR 배치 검증")
    parser.add_argument("--limit",     type=int,  default=0,  help="테스트할 최대 이미지 수 (0=전체)")
    parser.add_argument("--filter",    type=str,  default="", help="파일명 필터 문자열")
    parser.add_argument("--fail-only", action="store_true",   help="FAIL/REVIEW 케이스만 상세 출력")
    parser.add_argument("--log-level", type=str,  default="WARNING",
                        choices=["DEBUG", "INFO", "WARNING"],  help="로그 레벨")
    return parser.parse_args()


def collect_targets(limit: int = 0, filter_str: str = "") -> list[tuple[str, str]]:
    """data/carnumber/ 이미지 파일 목록에서 (경로, 기대값) 쌍 생성.
    파일명에서 확장자를 제거한 값이 기대 번호판이다 (예: 120가5871.jpeg → 120가5871).
    """
    exts = {".jpeg", ".jpg", ".png", ".bmp"}
    targets = []
    for p in sorted(CARNUMBER_DIR.iterdir()):
        if p.suffix.lower() not in exts:
            continue
        expected = p.stem
        if filter_str and filter_str not in p.name:
            continue
        targets.append((str(p), expected))
        if limit and len(targets) >= limit:
            break
    return targets


async def run_batch(targets: list[tuple[str, str]], fail_only: bool = False) -> None:
    from services.ocr_storage import run_ocr_on_file

    print("\n" + "=" * 70)
    print(f"  OCR 배치 검증  |  대상: {len(targets)}개")
    print("=" * 70)

    results = []
    total_start = time.monotonic()

    for idx, (src_path, expected) in enumerate(targets, 1):
        t0 = time.monotonic()
        result = await run_ocr_on_file(src_path)
        elapsed = time.monotonic() - t0

        plate = result["plate_number"]
        review = result["needs_review"]

        # MANUAL_REVIEW_REQUIRED: 프리픽스 제거 후 비교
        plate_norm = re.sub(r'^MANUAL_REVIEW_REQUIRED:', '', plate).replace(" ", "")
        expected_norm = expected.replace(" ", "")

        is_match = plate_norm == expected_norm
        if is_match:
            status, tag = PASS_STR, "✓"
        elif review:
            status, tag = WARN_STR, "△"
        else:
            status, tag = FAIL_STR, "✗"

        row = {
            "path": src_path,
            "expected": expected,
            "got": plate,
            "match": is_match,
            "review": review,
            "elapsed": elapsed,
        }
        results.append(row)

        if not fail_only or not is_match:
            print(
                f"  [{idx:>3}/{len(targets)}] {tag}  "
                f"{expected:>12}  →  {plate:<25}  {status}  ({elapsed:.1f}s)"
            )

    total_elapsed = time.monotonic() - total_start

    n_pass   = sum(1 for r in results if r["match"])
    n_review = sum(1 for r in results if not r["match"] and r["review"])
    n_fail   = sum(1 for r in results if not r["match"] and not r["review"])
    avg_t    = total_elapsed / len(results) if results else 0

    print("\n" + "=" * 70)
    print(f"  총 {len(results)}개  |  PASS: {n_pass}  REVIEW: {n_review}  FAIL: {n_fail}")
    print(f"  정확도: {n_pass / len(results) * 100:.1f}%  |  "
          f"총 소요: {total_elapsed:.0f}s  평균: {avg_t:.1f}s/장")
    print("=" * 70)

    fails = [r for r in results if not r["match"]]
    if fails:
        print(f"\n  [불일치 목록 — {len(fails)}건]")
        for r in fails:
            tag = "△" if r["review"] else "✗"
            print(f"    {tag}  {r['expected']:>12}  →  {r['got']}")
    print()


def main():
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s [%(name)s] %(message)s",
    )

    targets = collect_targets(limit=args.limit, filter_str=args.filter)
    if not targets:
        print(f"[ERROR] {CARNUMBER_DIR} 에서 이미지를 찾을 수 없습니다.")
        sys.exit(1)

    asyncio.run(run_batch(targets, fail_only=args.fail_only))


if __name__ == "__main__":
    main()
