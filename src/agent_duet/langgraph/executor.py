"""A2A v1 adapter for a compiled LangGraph."""

from __future__ import annotations

import asyncio
import logging
import uuid
from asyncio import CancelledError
from typing import Any

from a2a.helpers import new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from agent_duet.langgraph.agent import Graph

logger = logging.getLogger(__name__)


def message_text(message: BaseMessage) -> str:
    """Normalize LangChain string and content-block messages to plain text."""
    content = message.content
    if isinstance(content, str):
        return content

    chunks: list[str] = []
    for block in content:
        if isinstance(block, str):
            chunks.append(block)
        elif isinstance(block, dict):
            text = block.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "".join(chunks)


class LangGraphA2AExecutor(AgentExecutor):
    """Map A2A `context_id` to LangGraph `thread_id` and publish task events."""

    def __init__(self, graph: Graph, *, max_input_chars: int) -> None:
        self._graph = graph
        self._max_input_chars = max_input_chars
        self._running: dict[str, asyncio.Task[Any]] = {}
        self._running_lock = asyncio.Lock()

    async def _register(self, task_id: str) -> None:
        current = asyncio.current_task()
        if current is not None:
            async with self._running_lock:
                self._running[task_id] = current

    async def _unregister(self, task_id: str) -> None:
        async with self._running_lock:
            self._running.pop(task_id, None)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.context_id is None:
            raise ValueError("A2A context ID is required")
        task_id = context.task_id or ""
        async with self._running_lock:
            running = self._running.get(task_id)
        if running is not None:
            running.cancel()
        updater = TaskUpdater(event_queue, task_id, context.context_id)
        await updater.cancel()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.message is None or context.context_id is None:
            raise ValueError("A2A message and context ID are required")

        query = context.get_user_input()
        if len(query) > self._max_input_chars:
            raise ValueError(f"Input exceeds {self._max_input_chars} characters")

        task = context.current_task
        if task is None:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        updater = TaskUpdater(event_queue, task.id, context.context_id)
        await updater.submit()
        await self._register(task.id)

        try:
            await updater.start_work()
            config: RunnableConfig = {"configurable": {"thread_id": context.context_id}}
            final_state: dict[str, Any] | None = None
            last_progress: str | None = None

            async for state in self._graph.astream(
                {"messages": [HumanMessage(content=query)]},
                config=config,
                stream_mode="values",
            ):
                final_state = state
                messages = state.get("messages", [])
                if not messages:
                    continue

                latest = messages[-1]
                progress: str | None = None
                if isinstance(latest, AIMessage) and latest.tool_calls:
                    names = ", ".join(call["name"] for call in latest.tool_calls)
                    progress = f"Calling tools: {names}"
                elif isinstance(latest, ToolMessage):
                    progress = f"Tool completed: {latest.name or 'unnamed'}"

                if progress and progress != last_progress:
                    await updater.update_status(
                        state=TaskState.TASK_STATE_WORKING,
                        message=updater.new_agent_message([Part(text=progress)]),
                    )
                    last_progress = progress

            if final_state is None or not final_state.get("messages"):
                raise RuntimeError("LangGraph completed without a final state")

            final_message = final_state["messages"][-1]
            if not isinstance(final_message, AIMessage):
                raise RuntimeError("LangGraph completed without a final AI message")

            answer = message_text(final_message).strip()
            if not answer:
                raise RuntimeError("LangGraph completed with an empty answer")

            await updater.add_artifact(
                parts=[Part(text=answer)],
                artifact_id=str(uuid.uuid4()),
                name="architecture_review",
                last_chunk=True,
            )
            await updater.complete()
        except CancelledError:
            await updater.update_status(state=TaskState.TASK_STATE_CANCELED)
        except Exception:
            logger.exception("LangGraph A2A execution failed", extra={"context_id": context.context_id})
            await updater.update_status(
                state=TaskState.TASK_STATE_FAILED,
                message=updater.new_agent_message([Part(text="Agent execution failed.")]),
            )
        finally:
            await self._unregister(task.id)
