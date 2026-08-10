from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from agent_duet.langgraph.agent import build_langgraph_agent
from tests.fakes import BindableFakeChatModel


@pytest.mark.asyncio
async def test_explicit_graph_executes_tool_loop() -> None:
    model = BindableFakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "lookup_enterprise_control",
                        "args": {"control_id": "security"},
                        "id": "call-security",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="## Verdict\nNot ready.\n\n## Evidence\nSecurity control checked."),
        ]
    )
    graph = build_langgraph_agent(model)
    config: RunnableConfig = {"configurable": {"thread_id": "test-thread"}}

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "Review this architecture."}]},
        config=config,
    )

    assert any(isinstance(message, ToolMessage) for message in result["messages"])
    assert result["messages"][-1].content.startswith("## Verdict")


@pytest.mark.asyncio
async def test_thread_id_retains_conversation_state() -> None:
    model = BindableFakeChatModel(
        responses=[
            AIMessage(content="First answer"),
            AIMessage(content="Second answer"),
        ]
    )
    graph = build_langgraph_agent(model)
    config: RunnableConfig = {"configurable": {"thread_id": "same-context"}}

    await graph.ainvoke({"messages": [{"role": "user", "content": "First turn"}]}, config=config)
    second = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "Second turn"}]},
        config=config,
    )

    contents = [message.content for message in second["messages"]]
    assert contents == ["First turn", "First answer", "Second turn", "Second answer"]
