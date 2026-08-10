"""A2A server entry point for the MAF reviewer."""

from __future__ import annotations

import uvicorn
from agent_framework import Agent
from starlette.applications import Starlette

from agent_duet.a2a_common import MAF_IDENTITY, configure_logging, create_a2a_app, create_agent_card
from agent_duet.maf.agent import build_live_maf_agent
from agent_duet.maf.executor import StatefulMAFA2AExecutor
from agent_duet.settings import Settings, get_settings


def create_app(settings: Settings | None = None, agent: Agent | None = None) -> Starlette:
    """Create the MAF A2A ASGI application with injectable dependencies."""
    resolved = settings or get_settings()
    target = agent or build_live_maf_agent(resolved)
    card = create_agent_card(MAF_IDENTITY, str(resolved.maf_public_url))
    executor = StatefulMAFA2AExecutor(target, max_input_chars=resolved.max_input_chars)
    return create_a2a_app(agent_card=card, executor=executor, service_name="maf-reviewer")


def main() -> None:
    """Run the MAF server with environment-backed settings."""
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        create_app(settings),
        host=settings.maf_host,
        port=settings.maf_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
