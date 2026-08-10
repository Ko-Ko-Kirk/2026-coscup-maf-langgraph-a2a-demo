from __future__ import annotations

from typing import Any

from agent_framework import (
    AgentResponse,
    AgentResponseUpdate,
    AgentSession,
    Content,
    Message,
    ResponseStream,
)
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel


class BindableFakeChatModel(FakeMessagesListChatModel):
    """A deterministic fake that accepts the same tool binding as a live model."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> BindableFakeChatModel:
        del tools, kwargs
        return self


class StatefulFakeMAFAgent:
    """Small MAF protocol fake that exposes session continuity in its answer."""

    name = "Fake MAF Reviewer"

    def create_session(self, *, session_id: str | None = None) -> AgentSession:
        return AgentSession(session_id=session_id)

    def run(
        self,
        messages: Any = None,
        *,
        stream: bool = False,
        session: AgentSession | None = None,
        **_: Any,
    ) -> Any:
        del messages
        active_session = session or self.create_session()
        turn = int(active_session.state.get("turn", 0)) + 1
        active_session.state["turn"] = turn
        answer = f"MAF session turn {turn}"
        final = AgentResponse(messages=[Message("assistant", [Content.from_text(answer)])])

        if not stream:

            async def complete() -> AgentResponse[Any]:
                return final

            return complete()

        async def updates() -> Any:
            yield AgentResponseUpdate(
                contents=[Content.from_text(answer)],
                role="assistant",
                message_id=f"turn-{turn}",
            )

        return ResponseStream(updates(), finalizer=lambda _: final)
