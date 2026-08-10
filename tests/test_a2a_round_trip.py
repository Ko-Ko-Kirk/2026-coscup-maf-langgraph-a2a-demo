from __future__ import annotations

import httpx
import pytest
from agent_framework.a2a import A2AAgent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from pydantic import HttpUrl

from agent_duet.a2a_common import LANGGRAPH_IDENTITY, create_agent_card
from agent_duet.langgraph.agent import build_langgraph_agent
from agent_duet.langgraph.server import create_app
from agent_duet.settings import Settings
from tests.fakes import BindableFakeChatModel


@pytest.mark.asyncio
async def test_maf_a2a_agent_calls_langgraph_asgi_server() -> None:
    model: FakeMessagesListChatModel = BindableFakeChatModel(
        responses=[AIMessage(content="LangGraph answer over A2A")]
    )
    graph = build_langgraph_agent(model)
    settings = Settings(
        foundry_project_endpoint="https://unused.example/api/projects/test",
        foundry_model="unused",
        langgraph_public_url=HttpUrl("http://langgraph.test/"),
    )
    app = create_app(settings=settings, graph=graph)
    card = create_agent_card(LANGGRAPH_IDENTITY, "http://langgraph.test/")
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://langgraph.test") as client:
        # The caller owns this injected HTTP client. Avoid asking the beta
        # A2AAgent context manager to close it.
        remote = A2AAgent(
            name=card.name,
            description=card.description,
            agent_card=card,
            url="http://langgraph.test/",
            http_client=client,
            supported_protocol_bindings=["JSONRPC"],
        )
        response = await remote.run("Review this architecture.")

    assert response.text == "LangGraph answer over A2A"
