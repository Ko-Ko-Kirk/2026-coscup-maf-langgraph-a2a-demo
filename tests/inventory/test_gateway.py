from __future__ import annotations

import httpx
import pytest

from agent_duet.scenarios.inventory.contracts import InventorySource
from agent_duet.scenarios.inventory.gateway import InventoryGateway


def _gateway(
    client: httpx.AsyncClient,
    *,
    max_attempts: int = 1,
    fallback_to_fixture: bool = False,
) -> InventoryGateway:
    return InventoryGateway(
        base_url="https://inventory.test/inventory/",
        mode="live",
        timeout_seconds=1,
        max_attempts=max_attempts,
        retry_delay_seconds=0,
        fallback_to_fixture=fallback_to_fixture,
        client=client,
    )


@pytest.mark.asyncio
async def test_live_gateway_validates_and_returns_one_observation() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.params["prod"] == "火雞肉飯"
        return httpx.Response(200, json={"inventory": 23, "prod": "火雞肉飯"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        observation = await _gateway(client).get_inventory("火雞肉飯")

    assert calls == 1
    assert observation.inventory == 23
    assert observation.source == InventorySource.LIVE
    assert observation.catalog_verified is False
    assert observation.warning is not None


@pytest.mark.asyncio
async def test_gateway_retries_503_then_succeeds() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, json={"detail": "cold start"})
        return httpx.Response(200, json={"inventory": 7, "prod": "雞排"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        observation = await _gateway(client, max_attempts=2).get_inventory("雞排")

    assert calls == 2
    assert observation.inventory == 7


@pytest.mark.asyncio
async def test_gateway_does_not_retry_422_and_labels_fallback() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(422, json={"detail": "bad product"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        observation = await _gateway(
            client,
            max_attempts=3,
            fallback_to_fixture=True,
        ).get_inventory("火雞肉飯")

    assert calls == 1
    assert observation.inventory == 30
    assert observation.source == InventorySource.FIXTURE_FALLBACK
    assert "must not authorize" in (observation.warning or "")


@pytest.mark.asyncio
async def test_fixture_mode_is_deterministic_and_unknown_product_is_zero() -> None:
    gateway = InventoryGateway(
        base_url="https://unused.test/",
        mode="fixture",
        timeout_seconds=1,
        max_attempts=1,
        retry_delay_seconds=0,
        fallback_to_fixture=False,
    )

    first = await gateway.get_inventory("火雞肉飯")
    second = await gateway.get_inventory("火雞肉飯")
    unknown = await gateway.get_inventory("不存在的商品")

    assert first.inventory == second.inventory == 30
    assert first.source == second.source == InventorySource.FIXTURE
    assert unknown.inventory == 0
    assert unknown.catalog_verified is False
