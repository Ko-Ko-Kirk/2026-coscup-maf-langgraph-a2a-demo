from __future__ import annotations

from typing import cast

import httpx
import pytest
from agent_framework import SupportsAgentRun
from agent_framework.a2a import A2AAgent

from agent_duet.a2a_common import MAF_IDENTITY, create_a2a_app, create_agent_card
from agent_duet.maf.executor import StatefulMAFA2AExecutor
from tests.fakes import StatefulFakeMAFAgent


@pytest.mark.asyncio
async def test_maf_a2a_session_survives_two_protocol_turns() -> None:
    fake = cast(SupportsAgentRun, StatefulFakeMAFAgent())
    executor = StatefulMAFA2AExecutor(fake, max_input_chars=1_000)
    card = create_agent_card(MAF_IDENTITY, "http://maf.test/")
    app = create_a2a_app(agent_card=card, executor=executor, service_name="maf-test")
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://maf.test") as client:
        remote = A2AAgent(
            name=card.name,
            description=card.description,
            agent_card=card,
            url="http://maf.test/",
            http_client=client,
            supported_protocol_bindings=["JSONRPC"],
        )
        session = remote.create_session()
        first = await remote.run("First", session=session)
        second = await remote.run("Second", session=session)

    assert first.text == "MAF session turn 1"
    assert second.text == "MAF session turn 2"
