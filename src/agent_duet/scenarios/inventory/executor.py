"""A2A adapter for the explicit inventory LangGraph workflow."""

from __future__ import annotations

import asyncio
import logging
import uuid
from asyncio import CancelledError
from typing import Any, cast

from a2a.helpers import new_task_from_user_message
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState
from langchain_core.runnables import RunnableConfig

from agent_duet.scenarios.inventory.contracts import InventoryDecision, InventoryObservation
from agent_duet.scenarios.inventory.graph import InventoryGraph, InventoryState

logger = logging.getLogger(__name__)


class InventoryA2AExecutor(AgentExecutor):
    """Expose an inventory graph through A2A while preserving context identity."""

    def __init__(self, graph: InventoryGraph, *, max_input_chars: int) -> None:
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
            await updater.start_work(
                message=updater.new_agent_message([Part(text="Parsing inventory request.")])
            )
            config: RunnableConfig = {"configurable": {"thread_id": context.context_id}}
            final_state: InventoryState | None = None
            observation_announced = False
            decision_announced = False

            async for raw_state in self._graph.astream(
                {"request_text": query},
                config=config,
                stream_mode="values",
            ):
                state = cast(InventoryState, raw_state)
                final_state = state

                observation = state.get("observation")
                if isinstance(observation, InventoryObservation) and not observation_announced:
                    await updater.update_status(
                        state=TaskState.TASK_STATE_WORKING,
                        message=updater.new_agent_message(
                            [Part(text=f"Inventory observed from {observation.source.value}.")]
                        ),
                    )
                    observation_announced = True

                decision = state.get("decision")
                if isinstance(decision, InventoryDecision) and not decision_announced:
                    await updater.update_status(
                        state=TaskState.TASK_STATE_WORKING,
                        message=updater.new_agent_message(
                            [Part(text=f"Inventory decision: {decision.status.value}.")]
                        ),
                    )
                    decision_announced = True

            if final_state is None:
                raise RuntimeError("Inventory graph completed without state")
            report = final_state.get("report", "").strip()
            if not report:
                raise RuntimeError("Inventory graph completed without an A2A report")

            await updater.add_artifact(
                parts=[Part(text=report)],
                artifact_id=str(uuid.uuid4()),
                name="inventory_availability_decision",
                last_chunk=True,
            )
            await updater.complete()
        except CancelledError:
            await updater.update_status(state=TaskState.TASK_STATE_CANCELED)
        except Exception:
            logger.exception(
                "Inventory A2A execution failed",
                extra={"context_id": context.context_id},
            )
            await updater.update_status(
                state=TaskState.TASK_STATE_FAILED,
                message=updater.new_agent_message([Part(text="Inventory agent execution failed.")]),
            )
        finally:
            await self._unregister(task.id)
