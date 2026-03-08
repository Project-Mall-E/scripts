"""Tests for orchestrator."""

from unittest.mock import AsyncMock, patch

import pytest

from get_store_url_and_tags.config import Config
from get_store_url_and_tags.models import DiscoveredURL, StoreLink
from get_store_url_and_tags.orchestrator import DiscoveryOrchestrator
from get_store_url_and_tags.models.store import StoreDefinition
from get_store_url_and_tags.config import Settings


def _make_config() -> Config:
    store = StoreDefinition(
        name="TestStore",
        homepage="https://www.teststore.com",
        domain="teststore.com",
        discovery_strategy="auto",
    )
    settings = Settings(rate_limit_seconds=1.0, request_timeout_seconds=10.0)
    return Config(stores=[store], settings=settings)


@pytest.mark.asyncio
async def test_run_returns_entries_from_pipeline() -> None:
    config = _make_config()
    expected_link = StoreLink(
        name="TestStore",
        url="https://www.teststore.com/womens/tops",
        tags=["Womens", "Tops"],
    )
    with patch.object(DiscoveryOrchestrator, "_discover_store", new_callable=AsyncMock) as mock_discover:
        mock_discover.return_value = [
            DiscoveredURL(
                url=expected_link.url,
                store_name=expected_link.name,
                nav_text="Tops",
                discovery_method="sitemap",
            )
        ]
        with patch("get_store_url_and_tags.orchestrator.pipeline_process", new_callable=AsyncMock) as mock_pipeline:
            mock_pipeline.return_value = [expected_link]
            with patch("get_store_url_and_tags.orchestrator.setup_logging"):
                orch = DiscoveryOrchestrator(config=config)
                orch._sitemap_discovery.close = AsyncMock()
                orch._nav_discovery.close = AsyncMock()
                orch._link_discovery.close = AsyncMock()
                entries = await orch.run(stores=None)
                await orch.close()
    assert len(entries) == 1
    assert entries[0].url == expected_link.url
    assert entries[0].tags == expected_link.tags
    mock_discover.assert_called()
    mock_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_run_stores_filter() -> None:
    config = _make_config()
    with patch.object(DiscoveryOrchestrator, "_discover_store", new_callable=AsyncMock, return_value=[]):
        with patch("get_store_url_and_tags.orchestrator.pipeline_process", new_callable=AsyncMock, return_value=[]):
            with patch("get_store_url_and_tags.orchestrator.setup_logging"):
                orch = DiscoveryOrchestrator(config=config)
                orch._sitemap_discovery.close = AsyncMock()
                orch._nav_discovery.close = AsyncMock()
                orch._link_discovery.close = AsyncMock()
                entries = await orch.run(stores=["TestStore"])
                await orch.close()
    assert entries == []


@pytest.mark.asyncio
async def test_run_empty_stores_list() -> None:
    config = _make_config()
    with patch("get_store_url_and_tags.orchestrator.setup_logging"):
        orch = DiscoveryOrchestrator(config=config)
        orch._sitemap_discovery.close = AsyncMock()
        orch._nav_discovery.close = AsyncMock()
        orch._link_discovery.close = AsyncMock()
        entries = await orch.run(stores=["NonExistentStore"])
        await orch.close()
    assert entries == []


@pytest.mark.asyncio
async def test_discover_store_sitemap_strategy_returns_early() -> None:
    store = StoreDefinition(
        name="S",
        homepage="https://s.com",
        domain="s.com",
        discovery_strategy="sitemap",
    )
    config = Config(stores=[store], settings=Settings())
    orch = DiscoveryOrchestrator(config=config)
    orch._sitemap_discovery.discover = AsyncMock(
        return_value=[DiscoveredURL(url="https://s.com/cat", store_name="S", discovery_method="sitemap")]
    )
    orch._nav_discovery.discover = AsyncMock()
    orch._link_discovery.discover = AsyncMock()
    result = await orch._discover_store(store)
    assert len(result) == 1
    orch._sitemap_discovery.discover.assert_called_once()
    orch._nav_discovery.discover.assert_not_called()
    orch._link_discovery.discover.assert_not_called()
