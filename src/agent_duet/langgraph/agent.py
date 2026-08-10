"""The explicit LangGraph agent loop under comparison."""

from __future__ import annotations

from typing import Any

from azure.core.credentials import TokenCredential
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent_duet.auth import build_credential
from agent_duet.langgraph.tools import LANGGRAPH_TOOLS
from agent_duet.prompts import LANGGRAPH_SYSTEM_PROMPT
from agent_duet.settings import Settings

type Graph = CompiledStateGraph[Any, Any, Any, Any]


def build_langgraph_agent(
    model: BaseChatModel,
    *,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> Graph:
    """Build an explicit ReAct-style graph with the same prompt and tools as MAF.

    Unlike MAF's `Agent`, the model node, tool node, loop edge, termination
    condition, state reducer, and checkpointer are visible application code.
    """
    model_with_tools = model.bind_tools(LANGGRAPH_TOOLS)

    async def call_model(state: MessagesState) -> dict[str, list[BaseMessage]]:
        response = await model_with_tools.ainvoke(
            [SystemMessage(content=LANGGRAPH_SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(LANGGRAPH_TOOLS))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            "__end__": END,
        },
    )
    builder.add_edge("tools", "agent")

    resolved_checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
    return builder.compile(checkpointer=resolved_checkpointer, name="langgraph-runtime-reviewer")


def build_live_langgraph_agent(
    settings: Settings,
    credential: TokenCredential | None = None,
) -> Graph:
    """Create the live LangGraph reviewer backed by the same Foundry project."""
    settings.require_foundry()
    resolved_credential = credential or build_credential(settings)
    model = AzureAIOpenAIApiChatModel(
        project_endpoint=settings.foundry_project_endpoint,
        model=settings.foundry_model,
        credential=resolved_credential,
    )
    return build_langgraph_agent(model)
