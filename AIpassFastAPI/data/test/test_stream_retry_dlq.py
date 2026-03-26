"""
Unit tests for POST /api/v1/stream/retry-dlq endpoint.

Framework: pytest + pytest-asyncio (asyncio_mode=auto)
Transport: httpx.AsyncClient + ASGITransport (no real server needed)
Mock target: services.webhook_client.webhook_client.retry_failed_payloads
"""

import os
import json
import pytest
import pytest_asyncio
import httpx
from unittest.mock import AsyncMock, patch

# ── app import ──────────────────────────────────────────────────────────────
# main.py's lifespan runs startup tasks (Vision engine, http_client, etc.).
# We bypass it entirely by importing *stream.router* directly and mounting it
# on a bare FastAPI instance — no side-effects, no network dependency.
from fastapi import FastAPI
from api import stream as stream_module

# Minimal app that mirrors the real prefix used in main.py
_app = FastAPI()
_app.include_router(stream_module.router, prefix="/api/v1")

# Path constant shared between production code and these tests
DLQ_PATH = "data/fallback_queue.jsonl"


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def async_client():
    """Provide a reusable AsyncClient wired to the test app via ASGITransport."""
    transport = httpx.ASGITransport(app=_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def isolate_dlq(tmp_path, monkeypatch):
    """
    Redirect all DLQ file access to a temporary directory for each test.

    stream.py uses  os.path.exists(dlq_path)  and  open(dlq_path, ...)
    with the literal string "data/fallback_queue.jsonl".
    We monkeypatch os.path.exists and the builtin open inside the stream
    module so that each test operates on a fresh tmp location.
    """
    # Resolve a unique DLQ path inside pytest's tmp_path
    tmp_dlq = str(tmp_path / "fallback_queue.jsonl")
    # Store so individual tests can write seed data if needed
    isolate_dlq._tmp_dlq = tmp_dlq

    original_exists = os.path.exists

    def patched_exists(path):
        if path == DLQ_PATH:
            return original_exists(tmp_dlq)
        return original_exists(path)

    original_open = open

    def patched_open(path, *args, **kwargs):
        if path == DLQ_PATH:
            return original_open(tmp_dlq, *args, **kwargs)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(stream_module.os.path, "exists", patched_exists)
    monkeypatch.setattr("builtins.open", patched_open)

    yield tmp_dlq


# ── helper ───────────────────────────────────────────────────────────────────

def _write_dlq(tmp_dlq: str, payloads: list[dict]):
    """Seed the temp DLQ file with the given payloads (one JSON per line)."""
    with open(tmp_dlq, "w", encoding="utf-8") as f:
        for p in payloads:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


# ── test cases ────────────────────────────────────────────────────────────────

class TestRetryDlqEndpoint:
    """POST /api/v1/stream/retry-dlq"""

    # ── Case 1: DLQ 파일 없을 때 ──────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_no_dlq_file_returns_pending_zero(self, async_client, isolate_dlq):
        """DLQ 파일이 존재하지 않으면 pending=0을 반환하고 retry는 호출하지 않는다."""
        # Guarantee tmp file does NOT exist (fixture already ensures this,
        # but be explicit for readability)
        tmp_dlq = isolate_dlq
        if os.path.exists(tmp_dlq):
            os.remove(tmp_dlq)

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ) as mock_retry:
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["pending"] == 0
        # The exact message from production code
        assert "DLQ 파일 없음" in body["message"]
        # retry must NOT be called when there is no file
        mock_retry.assert_not_called()

    # ── Case 2: DLQ 파일 있을 때 ──────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_dlq_file_present_returns_pending_count_and_calls_retry(
        self, async_client, isolate_dlq
    ):
        """DLQ 파일이 존재하면 pending 건수를 반환하고 retry_failed_payloads를 호출한다."""
        tmp_dlq = isolate_dlq
        payloads = [
            {"eventId": "EVT-001", "plateNumber": "12가1234"},
            {"eventId": "EVT-002", "plateNumber": "34나5678"},
            {"eventId": "EVT-003", "plateNumber": "56다9012"},
        ]
        _write_dlq(tmp_dlq, payloads)

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ) as mock_retry:
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["pending"] == 3
        # retry must be called exactly once
        mock_retry.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dlq_file_single_entry_returns_pending_one(
        self, async_client, isolate_dlq
    ):
        """DLQ에 항목이 정확히 1건일 때 pending=1을 반환한다 (경계값 검증)."""
        tmp_dlq = isolate_dlq
        _write_dlq(tmp_dlq, [{"eventId": "EVT-SINGLE"}])

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ):
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.status_code == 200
        assert response.json()["pending"] == 1

    @pytest.mark.asyncio
    async def test_dlq_file_empty_returns_pending_zero(
        self, async_client, isolate_dlq
    ):
        """DLQ 파일이 존재하지만 내용이 비어 있으면 pending=0을 반환한다."""
        tmp_dlq = isolate_dlq
        # Create an empty file
        open(tmp_dlq, "w").close()

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ) as mock_retry:
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["pending"] == 0
        # retry is still called — file exists even if empty
        mock_retry.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dlq_file_with_blank_lines_counts_only_non_blank(
        self, async_client, isolate_dlq
    ):
        """DLQ 파일에 공백 줄이 섞여 있어도 실제 항목 수만 pending에 반영한다."""
        tmp_dlq = isolate_dlq
        with open(tmp_dlq, "w", encoding="utf-8") as f:
            f.write(json.dumps({"eventId": "EVT-A"}) + "\n")
            f.write("\n")           # blank line — must be ignored
            f.write("   \n")        # whitespace-only line — must be ignored
            f.write(json.dumps({"eventId": "EVT-B"}) + "\n")

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ):
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.status_code == 200
        assert response.json()["pending"] == 2

    # ── Case 3: DLQ 파일 읽기 오류 시 ────────────────────────────────────
    @pytest.mark.asyncio
    async def test_dlq_read_error_returns_pending_minus_one_and_still_retries(
        self, async_client, isolate_dlq, monkeypatch
    ):
        """DLQ 파일 읽기 중 예외가 발생하면 pending=-1을 반환하되 retry는 여전히 호출된다."""
        tmp_dlq = isolate_dlq

        # Make the file exist so the endpoint proceeds past the os.path.exists check
        _write_dlq(tmp_dlq, [{"eventId": "EVT-ERR"}])

        # Patch open so that reading raises an IOError
        original_open = open

        def broken_open(path, *args, **kwargs):
            if path == DLQ_PATH:
                raise IOError("Simulated read failure")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", broken_open)

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ) as mock_retry:
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["pending"] == -1
        # retry must still be called even after the read error
        mock_retry.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dlq_permission_error_returns_pending_minus_one_and_still_retries(
        self, async_client, isolate_dlq, monkeypatch
    ):
        """PermissionError도 읽기 오류로 처리되어 pending=-1이 반환된다."""
        tmp_dlq = isolate_dlq
        _write_dlq(tmp_dlq, [{"eventId": "EVT-PERM"}])

        original_open = open

        def permission_denied_open(path, *args, **kwargs):
            if path == DLQ_PATH:
                raise PermissionError("Simulated permission denied")
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr("builtins.open", permission_denied_open)

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ) as mock_retry:
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["pending"] == -1
        mock_retry.assert_awaited_once()

    # ── Response shape invariants ─────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_response_always_contains_required_keys(
        self, async_client, isolate_dlq
    ):
        """성공/실패와 무관하게 응답에는 항상 success, pending, message 키가 포함된다."""
        # Case A: no file
        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ):
            resp_no_file = await async_client.post("/api/v1/stream/retry-dlq")

        for key in ("success", "pending", "message"):
            assert key in resp_no_file.json(), f"Key '{key}' missing when no DLQ file"

        # Case B: file present
        tmp_dlq = isolate_dlq
        _write_dlq(tmp_dlq, [{"eventId": "EVT-SHAPE"}])

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ):
            resp_with_file = await async_client.post("/api/v1/stream/retry-dlq")

        for key in ("success", "pending", "message"):
            assert key in resp_with_file.json(), f"Key '{key}' missing when DLQ file exists"

    @pytest.mark.asyncio
    async def test_success_flag_is_always_true(self, async_client, isolate_dlq):
        """retry-dlq 엔드포인트는 어떤 경우에도 success=True를 반환한다 (오류 은닉 정책)."""
        tmp_dlq = isolate_dlq
        _write_dlq(tmp_dlq, [{"eventId": "EVT-X"}])

        with patch.object(
            stream_module.webhook_client,
            "retry_failed_payloads",
            new_callable=AsyncMock,
        ):
            response = await async_client.post("/api/v1/stream/retry-dlq")

        assert response.json()["success"] is True
