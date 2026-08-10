"""Stateful A2A hosting adapter for a Microsoft Agent Framework agent."""

from __future__ import annotations

import asyncio
import logging
import uuid
from asyncio import CancelledError
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from a2a.helpers import new_task_from_user_message
from a2a.server.agent_execution import RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState
from agent_framework import AgentResponse, AgentResponseUpdate, AgentSession, ResponseStream, SupportsAgentRun
from agent_framework.a2a import A2AExecutor

logger = logging.getLogger(__name__)


class InMemorySessionRegistry:
    """Serialize access to MAF sessions by A2A context ID.

    This is intentionally an in-memory demo implementation. A production host
    must replace it with tenant-bound durable storage and eviction.
    """

    def __init__(self, agent: SupportsAgentRun) -> None:
        self._agent = agent
        self._sessions: dict[str, AgentSession] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _lock_for(self, context_id: str) -> asyncio.Lock:
        async with self._registry_lock:
            return self._locks.setdefault(context_id, asyncio.Lock())

    @asynccontextmanager
    async def use(self, context_id: str) -> AsyncGenerator[AgentSession]:
        """Yield the one mutable session associated with an A2A conversation."""
        lock = await self._lock_for(context_id)
        async with lock:
            session = self._sessions.get(context_id)
            if session is None:
                session = self._agent.create_session(session_id=f"a2a:{context_id}")
                self._sessions[context_id] = session
            yield session


class StatefulMAFA2AExecutor(A2AExecutor):
    """MAF's A2A executor with explicit in-process multi-turn session retention.

    The upstream `A2AExecutor.handle_events` performs the MAF-to-A2A content
    conversion. This subclass only owns the application-level session policy.
    """

    def __init__(self, agent: SupportsAgentRun, *, max_input_chars: int) -> None:
        super().__init__(agent=agent, stream=True)
        self._target = agent
        self._sessions = InMemorySessionRegistry(agent)
        self._max_input_chars = max_input_chars

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        if context.context_id is None:
            raise ValueError("A2A context ID is required")
        updater = TaskUpdater(event_queue, context.task_id or "", context.context_id)
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

        try:
            await updater.start_work()
            async with self._sessions.use(context.context_id) as session:
                run_result = self._target.run(query, session=session, stream=True)
                stream = cast(
                    ResponseStream[AgentResponseUpdate, AgentResponse[Any]],
                    run_result,
                )
                artifact_ids: set[str] = set()
                default_artifact_id = str(uuid.uuid4())

                async for update in stream:
                    await self.handle_events(
                        update,
                        updater,
                        streamed_artifact_ids=artifact_ids,
                        default_artifact_id=default_artifact_id,
                    )

                final_response = await stream.get_final_response()
                if not artifact_ids:
                    for message in final_response.messages:
                        await self.handle_events(message, updater)

            await updater.complete()
        except CancelledError:
            await updater.update_status(state=TaskState.TASK_STATE_CANCELED)
        except Exception:
            logger.exception("MAF A2A execution failed", extra={"context_id": context.context_id})
            await updater.update_status(
                state=TaskState.TASK_STATE_FAILED,
                message=updater.new_agent_message([Part(text="Agent execution failed.")]),
            )
