"""Tests for utils.rate_limiter."""

from unittest.mock import patch

import pytest

from get_store_url_and_tags.utils.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_acquire_updates_time() -> None:
    with patch("get_store_url_and_tags.utils.rate_limiter.time") as mock_time:
        mock_time.monotonic.side_effect = [0.0, 2.0]  # now, then after sleep
        r = RateLimiter(default_delay=2.0, jitter_seconds=0.0)
        with patch("asyncio.sleep"):
            await r.acquire("example.com")
        assert r._last_request_time["example.com"] == 2.0


@pytest.mark.asyncio
async def test_acquire_two_domains_independent() -> None:
    with patch("get_store_url_and_tags.utils.rate_limiter.time") as mock_time:
        mock_time.monotonic.return_value = 100.0
        r = RateLimiter(default_delay=10.0, jitter_seconds=0.0)
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None
            await r.acquire("a.com")
            await r.acquire("b.com")
        assert "a.com" in r._last_request_time
        assert "b.com" in r._last_request_time


@pytest.mark.asyncio
async def test_acquire_waits_when_elapsed_less_than_delay() -> None:
    with patch("get_store_url_and_tags.utils.rate_limiter.time") as mock_time:
        # elapsed=1 (now=1, last=0), delay=2 -> wait 1
        mock_time.monotonic.side_effect = [1.0, 2.0]
        r = RateLimiter(default_delay=2.0, jitter_seconds=0.0)
        slept = []
        async def capture_sleep(sec):
            slept.append(sec)
        with patch("asyncio.sleep", side_effect=capture_sleep):
            await r.acquire("x.com")
        assert len(slept) == 1
        assert slept[0] == 1.0


def test_reset_domain() -> None:
    r = RateLimiter()
    r._last_request_time["a.com"] = 100.0
    r.reset("a.com")
    assert r._last_request_time["a.com"] == 0


def test_reset_all() -> None:
    r = RateLimiter()
    r._last_request_time["a.com"] = 100.0
    r._last_request_time["b.com"] = 200.0
    r.reset(None)
    assert len(r._last_request_time) == 0
