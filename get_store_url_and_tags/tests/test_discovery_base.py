"""Tests for discovery.base."""

from unittest.mock import AsyncMock

import pytest

from get_store_url_and_tags.discovery.base import DiscoveryStrategy
from get_store_url_and_tags.models import DiscoveredURL, StoreDefinition


class ConcreteStrategy(DiscoveryStrategy):
    """Concrete implementation for testing."""

    name = "concrete"

    async def discover(
        self,
        store: StoreDefinition,
        **kwargs
    ) -> list:
        return [
            DiscoveredURL(
                url="https://example.com/cat",
                store_name=store.name,
                discovery_method="concrete",
            )
        ]


@pytest.mark.asyncio
async def test_discovery_strategy_discover(sample_store_definition: StoreDefinition) -> None:
    strategy = ConcreteStrategy()
    result = await strategy.discover(sample_store_definition)
    assert len(result) == 1
    assert result[0].url == "https://example.com/cat"
    assert result[0].store_name == sample_store_definition.name
    assert result[0].discovery_method == "concrete"


def test_discovery_strategy_repr() -> None:
    strategy = ConcreteStrategy()
    assert repr(strategy) == "<ConcreteStrategy>"
