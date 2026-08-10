from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from agent_duet.client import collaboration


@dataclass
class FakeRemoteAgent:
    name: str
    answers: list[str]

    def __post_init__(self) -> None:
        self.calls: list[tuple[str, object | None]] = []

    async def __aenter__(self) -> FakeRemoteAgent:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def create_session(self) -> object:
        return object()

    async def run(self, prompt: str, *, session: object | None = None) -> SimpleNamespace:
        self.calls.append((prompt, session))
        return SimpleNamespace(text=self.answers.pop(0))


@pytest.mark.asyncio
async def test_collaboration_relays_artifacts_and_reuses_maf_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    maf = FakeRemoteAgent("maf", ["MAF initial", "MAF synthesis"])
    langgraph = FakeRemoteAgent("langgraph", ["LangGraph critique"])

    async def fake_resolve_card(base_url: str, *, timeout_seconds: float) -> SimpleNamespace:
        del timeout_seconds
        return SimpleNamespace(name=base_url)

    def fake_remote_agent(
        card: Any,
        base_url: str,
        *,
        timeout_seconds: float,
    ) -> FakeRemoteAgent:
        del card, timeout_seconds
        return maf if "maf" in base_url else langgraph

    monkeypatch.setattr(collaboration, "resolve_card", fake_resolve_card)
    monkeypatch.setattr(collaboration, "remote_agent", fake_remote_agent)

    result = await collaboration.collaborate(
        task="Original architecture brief",
        maf_url="http://maf.test/",
        langgraph_url="http://langgraph.test/",
        timeout_seconds=30,
    )

    assert result.maf_initial_review == "MAF initial"
    assert result.langgraph_peer_review == "LangGraph critique"
    assert result.maf_final_synthesis == "MAF synthesis"

    assert "MAF initial" in langgraph.calls[0][0]
    assert "LangGraph critique" in maf.calls[1][0]
    assert maf.calls[0][1] is maf.calls[1][1]
