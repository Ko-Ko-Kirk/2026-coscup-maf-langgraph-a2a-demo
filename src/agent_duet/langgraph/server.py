"""A2A server entry point for the LangGraph reviewer."""

from __future__ import annotations

import uvicorn
from starlette.applications import Starlette

from agent_duet.a2a_common import (
    LANGGRAPH_IDENTITY,
    configure_logging,
    create_a2a_app,
    create_agent_card,
)
from agent_duet.langgraph.agent import Graph, build_live_langgraph_agent
from agent_duet.langgraph.executor import LangGraphA2AExecutor
from agent_duet.settings import Settings, get_settings


def create_app(settings: Settings | None = None, graph: Graph | None = None) -> Starlette:
    """Create the LangGraph A2A ASGI application with injectable dependencies."""
    resolved = settings or get_settings()
    target = graph or build_live_langgraph_agent(resolved)
    card = create_agent_card(LANGGRAPH_IDENTITY, str(resolved.langgraph_public_url))
    executor = LangGraphA2AExecutor(target, max_input_chars=resolved.max_input_chars)
    return create_a2a_app(agent_card=card, executor=executor, service_name="langgraph-reviewer")


def main() -> None:
    """Run the LangGraph server with environment-backed settings."""
    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        create_app(settings),
        host=settings.langgraph_host,
        port=settings.langgraph_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
