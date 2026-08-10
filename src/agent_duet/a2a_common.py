"""A2A server primitives shared by both framework implementations."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from a2a.server.agent_execution import AgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentInterface, AgentSkill
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agent_duet import __version__


@dataclass(frozen=True, slots=True)
class AgentIdentity:
    """Public discovery metadata for one reviewer."""

    name: str
    description: str
    framework_tag: str


MAF_IDENTITY = AgentIdentity(
    name="MAF Enterprise Reviewer",
    description="Reviews agent architectures through an enterprise operations and governance lens.",
    framework_tag="microsoft-agent-framework",
)

LANGGRAPH_IDENTITY = AgentIdentity(
    name="LangGraph Runtime Reviewer",
    description="Reviews agent architectures through explicit graph, state, and recovery semantics.",
    framework_tag="langgraph",
)


def create_agent_card(
    identity: AgentIdentity,
    public_url: str,
    *,
    skills: Sequence[AgentSkill] | None = None,
) -> AgentCard:
    """Create an A2A v1 Agent Card, defaulting to the comparison skill."""
    normalized_url = f"{public_url.rstrip('/')}/"
    resolved_skills = list(skills) if skills is not None else [
        AgentSkill(
            id="review_agent_architecture",
            name="Review Agent Architecture",
            description=(
                "Review an AI agent architecture for governance, durability, observability, "
                "interoperability, and security risks."
            ),
            tags=["architecture", "enterprise", "a2a", identity.framework_tag],
            examples=[
                "Review this design: a customer-support agent can issue refunds without approval.",
            ],
            input_modes=["text/plain"],
            output_modes=["text/plain"],
        )
    ]
    return AgentCard(
        name=identity.name,
        description=identity.description,
        version=__version__,
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True, push_notifications=False),
        supported_interfaces=[
            AgentInterface(
                url=normalized_url,
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        skills=resolved_skills,
    )


def create_a2a_app(*, agent_card: AgentCard, executor: AgentExecutor, service_name: str) -> Starlette:
    """Build equivalent Starlette/A2A hosts for MAF and LangGraph."""
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    async def health(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "service": service_name, "a2a": "1.0"})

    return Starlette(
        routes=[
            Route("/healthz", endpoint=health, methods=["GET"]),
            *create_agent_card_routes(agent_card),
            *create_jsonrpc_routes(request_handler, "/", enable_v0_3_compat=False),
        ]
    )


def configure_logging(level: str) -> None:
    """Configure readable logs without logging prompts or model responses."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
