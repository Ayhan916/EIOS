"""M34.1 Tests — Exponential backoff retry mechanism."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from application.external_intelligence.connectors.base import run_with_retry


@pytest.mark.asyncio
async def test_retry_exponential_backoff_delays():
    """Delay between retries follows base_delay * 2^attempt pattern."""
    call_times: list[float] = []
    call_count = 0

    async def coro_factory():
        nonlocal call_count
        call_times.append(time.monotonic())
        call_count += 1
        if call_count < 3:
            raise ValueError("retry me")
        return "done"

    # Use very small base_delay for test speed
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await run_with_retry(
            coro_factory, max_retries=3, base_delay=1.0
        )

    assert result == "done"
    # asyncio.sleep called twice (after attempt 0 and attempt 1)
    assert mock_sleep.call_count == 2
    # First sleep: 1.0 * 2^0 = 1.0
    assert mock_sleep.call_args_list[0].args[0] == pytest.approx(1.0, abs=0.01)
    # Second sleep: 1.0 * 2^1 = 2.0
    assert mock_sleep.call_args_list[1].args[0] == pytest.approx(2.0, abs=0.01)


@pytest.mark.asyncio
async def test_retry_no_sleep_on_first_success():
    async def coro_factory():
        return "immediate"

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await run_with_retry(coro_factory, max_retries=3, base_delay=1.0)

    assert result == "immediate"
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_retry_raises_last_exception_after_exhaustion():
    class CustomError(Exception):
        pass

    async def coro_factory():
        raise CustomError("terminal")

    with (
        patch("asyncio.sleep", new_callable=AsyncMock),
        pytest.raises(CustomError, match="terminal"),
    ):
        await run_with_retry(coro_factory, max_retries=2, base_delay=0.1)


@pytest.mark.asyncio
async def test_retry_max_retries_zero_runs_once_and_raises():
    call_count = 0

    async def coro_factory():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        await run_with_retry(coro_factory, max_retries=0, base_delay=0.0)

    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_on_last_attempt():
    call_count = 0

    async def coro_factory():
        nonlocal call_count
        call_count += 1
        if call_count < 4:
            raise IOError("transient")
        return "ok"

    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await run_with_retry(coro_factory, max_retries=4, base_delay=0.1)

    assert result == "ok"
    assert call_count == 4
