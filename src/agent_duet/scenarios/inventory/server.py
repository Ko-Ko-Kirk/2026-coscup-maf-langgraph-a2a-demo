"""A2A server for the LangGraph inventory specialist."""

from __future__ import annotations

import uvicorn
from a2a.types import AgentSkill
from starlette.applications import Starlette

from agent_duet.a2a_common import (
    AgentIdentity,
    configure_logging,
    create_a2a_app,
    create_agent_card,
)
from agent_duet.scenarios.inventory.executor import InventoryA2AExecutor
from agent_duet.scenarios.inventory.graph import InventoryGraph, build_live_inventory_graph
from agent_duet.settings import Settings, get_settings

INVENTORY_IDENTITY = AgentIdentity(
    name="LangGraph Inventory Specialist",
    description=(
        "Checks one inventory observation and makes an explicit availability decision "
        "without reserving stock."
    ),
    framework_tag="langgraph-inventory",
)

INVENTORY_SKILL = AgentSkill(
    id="check_inventory_availability",
    name="Check Inventory Availability",
    description=(
        "Accept a JSON object with product and quantity, observe inventory once, "
        "and return sufficient, insufficient, or manual_review."
    ),
    tags=["inventory", "order", "langgraph", "a2a"],
    examples=['{"product":"火雞肉飯","quantity":20}'],
    input_modes=["text/plain"],
    output_modes=["text/plain"],
)


def create_app(
    settings: Settings | None = None,
    graph: InventoryGraph | None = None,
) -> Starlette:
    """Create the inventory A2A ASGI app with injectable graph dependencies."""
    resolved = settings or get_settings()
    target = graph or build_live_inventory_graph(resolved)
    card = create_agent_card(
        INVENTORY_IDENTITY,
        str(resolved.inventory_agent_public_url),
        skills=[INVENTORY_SKILL],
    )
    executor = InventoryA2AExecutor(target, max_input_chars=resolved.max_input_chars)
    return create_a2a_app(
        agent_card=card,
        executor=executor,
        service_name="langgraph-inventory-specialist",
    )


def main() -> None:
    """Run the inventory A2A server with environment-backed settings."""
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        create_app(settings),
        host=settings.inventory_agent_host,
        port=settings.inventory_agent_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
