"""Tests for filters.robots_checker."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from get_store_url_and_tags.filters.robots_checker import RobotsChecker


def test_get_robots_url() -> None:
    c = RobotsChecker()
    assert c._get_robots_url("https://example.com/page") == "https://example.com/robots.txt"


def test_get_domain() -> None:
    c = RobotsChecker()
    assert c._get_domain("https://example.com/path") == "example.com"


@pytest.mark.asyncio
async def test_fetch_robots_success_caches() -> None:
    c = RobotsChecker()
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="User-agent: *\nDisallow: /admin\n")
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=None)

    mock_session = MagicMock()
    # session.get() must return an object that supports "async with", not a coroutine
    mock_session.get = MagicMock(return_value=mock_response)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    with patch("get_store_url_and_tags.filters.robots_checker.aiohttp.ClientSession", return_value=mock_session):
        parser1 = await c._fetch_robots("example.com", "https://example.com/robots.txt")
        parser2 = await c._fetch_robots("example.com", "https://example.com/robots.txt")
    assert parser1 is not None
    assert parser2 is parser1


@pytest.mark.asyncio
async def test_fetch_robots_non_200_allows_all() -> None:
    c = RobotsChecker()
    mock_response = MagicMock()
    mock_response.status = 404

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        parser = await c._fetch_robots("example.com", "https://example.com/robots.txt")
        assert parser is None


@pytest.mark.asyncio
async def test_fetch_robots_exception_allows_all() -> None:
    c = RobotsChecker()
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session.get = AsyncMock(side_effect=OSError("network error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        parser = await c._fetch_robots("example.com", "https://example.com/robots.txt")
        assert parser is None


@pytest.mark.asyncio
async def test_is_allowed_no_parser() -> None:
    c = RobotsChecker()
    with patch.object(c, "_fetch_robots", new_callable=AsyncMock, return_value=None):
        allowed = await c.is_allowed("https://example.com/page")
        assert allowed is True


@pytest.mark.asyncio
async def test_is_allowed_parser_allows() -> None:
    c = RobotsChecker()
    mock_parser = MagicMock()
    mock_parser.can_fetch.return_value = True
    with patch.object(c, "_fetch_robots", new_callable=AsyncMock, return_value=mock_parser):
        allowed = await c.is_allowed("https://example.com/page")
        assert allowed is True


@pytest.mark.asyncio
async def test_is_allowed_parser_blocks() -> None:
    c = RobotsChecker()
    mock_parser = MagicMock()
    mock_parser.can_fetch.return_value = False
    with patch.object(c, "_fetch_robots", new_callable=AsyncMock, return_value=mock_parser):
        allowed = await c.is_allowed("https://example.com/admin")
        assert allowed is False


@pytest.mark.asyncio
async def test_filter_allowed() -> None:
    c = RobotsChecker()
    with patch.object(c, "is_allowed", new_callable=AsyncMock, side_effect=[True, False, True]):
        urls = ["https://a.com/1", "https://a.com/2", "https://a.com/3"]
        result = await c.filter_allowed(urls)
        assert result == ["https://a.com/1", "https://a.com/3"]


def test_clear_cache() -> None:
    c = RobotsChecker()
    c._parsers["example.com"] = MagicMock()
    c.clear_cache()
    assert len(c._parsers) == 0
