from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from a2a.client import A2ACardResolver
from agent_framework.a2a import A2AAgent
from pydantic import HttpUrl

from agent_duet.scenarios.inventory.contracts import InventoryObservation, InventorySource
from agent_duet.scenarios.inventory.graph import build_inventory_graph
from agent_duet.scenarios.inventory.server import create_app
from agent_duet.settings import Settings
from tests.inventory.test_graph import StubGateway


@pytest.mark.asyncio
async def test_maf_a2a_agent_calls_inventory_langgraph_server() -> None:
    gateway = StubGateway(
        observation=InventoryObservation(
            observation_id="obs-a2a",
            product="火雞肉飯",
            inventory=30,
            observed_at=datetime.now(UTC),
            source=InventorySource.LIVE,
        )
    )
    graph = build_inventory_graph(gateway)
    settings = Settings(
        foundry_project_endpoint="https://unused.example/api/projects/test",
        foundry_model="unused",
        inventory_agent_public_url=HttpUrl("http://inventory.test/"),
    )
    app = create_app(settings=settings, graph=graph)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://inventory.test") as client:
        resolver = A2ACardResolver(httpx_client=client, base_url="http://inventory.test")
        discovered_card = await resolver.get_agent_card()
        assert discovered_card.skills[0].id == "check_inventory_availability"
        remote = A2AAgent(
            name=discovered_card.name,
            description=discovered_card.description,
            agent_card=discovered_card,
            url="http://inventory.test/",
            http_client=client,
            supported_protocol_bindings=["JSONRPC"],
        )
        response = await remote.run('{"product":"火雞肉飯","quantity":20}')

    assert gateway.calls == 1
    assert '"status": "sufficient"' in response.text
    assert '"inventory": 30' in response.text
