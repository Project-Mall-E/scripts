"""Tests for utils.retry."""

from unittest.mock import patch

import pytest

from get_store_url_and_tags.utils.retry import retry_async, retry_with_backoff


@pytest.mark.asyncio
async def test_retry_with_backoff_success_first_try() -> None:
    @retry_with_backoff(max_retries=2, base_delay=0.1, exceptions=(ValueError,))
    async def ok():
        return 42
    with patch("asyncio.sleep"):
        result = await ok()
    assert result == 42


@pytest.mark.asyncio
async def test_retry_with_backoff_success_after_retry() -> None:
    calls = []
    @retry_with_backoff(max_retries=2, base_delay=0.1, exceptions=(ValueError,))
    async def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise ValueError("fail")
        return 43
    with patch("asyncio.sleep"):
        result = await flaky()
    assert result == 43
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_retry_with_backoff_max_retries_exceeded() -> None:
    @retry_with_backoff(max_retries=2, base_delay=0.1, exceptions=(ValueError,))
    async def fail():
        raise ValueError("always fail")
    with patch("asyncio.sleep"):
        with pytest.raises(ValueError, match="always fail"):
            await fail()


@pytest.mark.asyncio
async def test_retry_with_backoff_other_exception_not_caught() -> None:
    @retry_with_backoff(max_retries=2, exceptions=(ValueError,))
    async def raise_type_error():
        raise TypeError("not retried")
    with pytest.raises(TypeError, match="not retried"):
        await raise_type_error()


@pytest.mark.asyncio
async def test_retry_async_success_first_try() -> None:
    async def ok():
        return 99
    result = await retry_async(ok, max_retries=2, exceptions=(ValueError,))
    assert result == 99


@pytest.mark.asyncio
async def test_retry_async_success_after_retry() -> None:
    calls = []
    async def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise ValueError("x")
        return 100
    with patch("asyncio.sleep"):
        result = await retry_async(flaky, max_retries=2, exceptions=(ValueError,))
    assert result == 100
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_retry_async_final_failure() -> None:
    async def fail():
        raise ValueError("final")
    with patch("asyncio.sleep"):
        with pytest.raises(ValueError, match="final"):
            await retry_async(fail, max_retries=2, exceptions=(ValueError,))
