from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

from agent_framework.a2a import A2AAgent
from agent_framework.foundry import FoundryChatClient

from agent_duet.scenarios.inventory.orchestrator import (
    INVENTORY_ORCHESTRATOR_PROMPT,
    build_inventory_orchestrator,
)


def test_maf_orchestrator_uses_one_bounded_remote_a2a_tool() -> None:
    remote = A2AAgent(
        name="LangGraph Inventory Specialist",
        description="Checks inventory.",
        url="http://inventory.test/",
    )
    client = cast(FoundryChatClient, MagicMock(spec=FoundryChatClient))

    orchestrator = build_inventory_orchestrator(client, remote)

    tools = orchestrator.default_options["tools"]
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0].name == "check_inventory_via_a2a"
    assert tools[0].max_invocations == 1
    assert "manual_review" in INVENTORY_ORCHESTRATOR_PROMPT
    assert "not a reservation" in INVENTORY_ORCHESTRATOR_PROMPT
