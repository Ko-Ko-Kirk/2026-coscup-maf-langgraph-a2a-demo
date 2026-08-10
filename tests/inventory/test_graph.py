from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from agent_duet.scenarios.inventory.contracts import (
    InventoryObservation,
    InventorySource,
    InventoryStatus,
)
from agent_duet.scenarios.inventory.gateway import InventoryUnavailableError
from agent_duet.scenarios.inventory.graph import build_inventory_graph


@dataclass
class StubGateway:
    observation: InventoryObservation | None = None
    unavailable: bool = False
    calls: int = 0

    async def get_inventory(self, product: str) -> InventoryObservation:
        self.calls += 1
        if self.unavailable:
            raise InventoryUnavailableError("unavailable")
        if self.observation is None:
            raise AssertionError("Stub observation is required")
        assert product == self.observation.product
        return self.observation


def _observation(
    stock: int,
    *,
    source: InventorySource = InventorySource.LIVE,
) -> InventoryObservation:
    return InventoryObservation(
        observation_id="obs-1",
        product="火雞肉飯",
        inventory=stock,
        observed_at=datetime.now(UTC),
        source=source,
        catalog_verified=source == InventorySource.FIXTURE,
    )


async def _invoke(gateway: StubGateway, request: str, thread_id: str = "inventory-test"):
    graph = build_inventory_graph(gateway)
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke({"request_text": request}, config=config)


@pytest.mark.asyncio
async def test_graph_routes_sufficient_after_exactly_one_lookup() -> None:
    gateway = StubGateway(observation=_observation(30))

    state = await _invoke(gateway, '{"product":"火雞肉飯","quantity":20}')

    assert gateway.calls == 1
    assert state["decision"].status == InventoryStatus.SUFFICIENT
    assert state["decision"].can_fulfill is True
    assert '"status": "sufficient"' in state["report"]


@pytest.mark.asyncio
async def test_graph_routes_insufficient_after_exactly_one_lookup() -> None:
    gateway = StubGateway(observation=_observation(9))

    state = await _invoke(gateway, '{"product":"火雞肉飯","quantity":20}')

    assert gateway.calls == 1
    assert state["decision"].status == InventoryStatus.INSUFFICIENT
    assert state["decision"].can_fulfill is False


@pytest.mark.asyncio
async def test_graph_never_authorizes_fixture_fallback() -> None:
    gateway = StubGateway(
        observation=_observation(30, source=InventorySource.FIXTURE_FALLBACK)
    )

    state = await _invoke(gateway, '{"product":"火雞肉飯","quantity":20}')

    assert gateway.calls == 1
    assert state["decision"].status == InventoryStatus.MANUAL_REVIEW
    assert state["decision"].can_fulfill is None


@pytest.mark.asyncio
async def test_invalid_a2a_payload_does_not_call_inventory() -> None:
    gateway = StubGateway(observation=_observation(30))

    state = await _invoke(gateway, "please check 火雞肉飯")

    assert gateway.calls == 0
    assert state["decision"].status == InventoryStatus.MANUAL_REVIEW
    assert state["decision"].request is None


@pytest.mark.asyncio
async def test_unavailable_inventory_routes_to_manual_review() -> None:
    gateway = StubGateway(unavailable=True)

    state = await _invoke(gateway, '{"product":"火雞肉飯","quantity":20}')

    assert gateway.calls == 1
    assert state["decision"].status == InventoryStatus.MANUAL_REVIEW


@pytest.mark.asyncio
async def test_foundry_style_render_node_cannot_replace_machine_decision() -> None:
    gateway = StubGateway(observation=_observation(30))
    model = FakeMessagesListChatModel(
        responses=[AIMessage(content="The observation appears sufficient but is not a reservation.")]
    )
    graph = build_inventory_graph(gateway, model=model)
    config: RunnableConfig = {"configurable": {"thread_id": "render-test"}}

    state = await graph.ainvoke(
        {"request_text": '{"product":"火雞肉飯","quantity":20}'},
        config=config,
    )

    assert '"status": "sufficient"' in state["report"]
    assert '"inventory": 30' in state["report"]
    assert "appears sufficient but is not a reservation" in state["report"]


@pytest.mark.asyncio
async def test_same_thread_clears_stale_observation_on_invalid_second_turn() -> None:
    gateway = StubGateway(observation=_observation(30))
    graph = build_inventory_graph(gateway)
    config: RunnableConfig = {"configurable": {"thread_id": "same-inventory-context"}}

    await graph.ainvoke(
        {"request_text": '{"product":"火雞肉飯","quantity":20}'},
        config=config,
    )
    second = await graph.ainvoke({"request_text": "invalid"}, config=config)

    assert gateway.calls == 1
    assert second["observation"] is None
    assert second["decision"].status == InventoryStatus.MANUAL_REVIEW
