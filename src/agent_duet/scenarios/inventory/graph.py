"""Explicit LangGraph workflow for inventory availability decisions."""

from __future__ import annotations

import json
from typing import Any, Literal, TypedDict

from azure.core.credentials import TokenCredential
from langchain_azure_ai.chat_models import AzureAIOpenAIApiChatModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from agent_duet.auth import build_credential
from agent_duet.scenarios.inventory.contracts import (
    InventoryDecision,
    InventoryObservation,
    InventoryRequest,
    InventorySource,
    InventoryStatus,
    parse_inventory_request,
)
from agent_duet.scenarios.inventory.gateway import (
    InventoryGateway,
    InventoryUnavailableError,
    SupportsInventoryLookup,
)
from agent_duet.settings import Settings

type InventoryGraph = CompiledStateGraph[Any, Any, Any, Any]


class InventoryState(TypedDict, total=False):
    """State visible to the source-code-reading audience."""

    request_text: str
    request: InventoryRequest | None
    observation: InventoryObservation | None
    decision: InventoryDecision | None
    error: str | None
    report: str


def _message_text(message: BaseMessage) -> str:
    if isinstance(message.content, str):
        return message.content
    chunks: list[str] = []
    for block in message.content:
        if isinstance(block, str):
            chunks.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            chunks.append(block["text"])
    return "".join(chunks)


def _deterministic_explanation(decision: InventoryDecision) -> str:
    if decision.status == InventoryStatus.SUFFICIENT:
        return "Observed stock covers the requested quantity, subject to catalog validation and reservation."
    if decision.status == InventoryStatus.INSUFFICIENT:
        return "Observed stock is below the requested quantity; do not promise fulfillment."
    return "No live inventory-backed fulfillment decision is available; route the order to a human."


def build_inventory_graph(
    gateway: SupportsInventoryLookup,
    *,
    model: BaseChatModel | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> InventoryGraph:
    """Build a deterministic decision graph with an optional Foundry explanation node."""

    async def parse_request(state: InventoryState) -> InventoryState:
        try:
            request = parse_inventory_request(state.get("request_text", ""))
        except (json.JSONDecodeError, ValidationError, ValueError):
            return {
                "request": None,
                "observation": None,
                "decision": None,
                "error": "invalid_request",
                "report": "",
            }
        return {
            "request": request,
            "observation": None,
            "decision": None,
            "error": None,
            "report": "",
        }

    def route_after_parse(state: InventoryState) -> Literal["lookup_inventory", "manual_review"]:
        return "lookup_inventory" if state.get("request") is not None else "manual_review"

    async def lookup_inventory(state: InventoryState) -> InventoryState:
        request = state.get("request")
        if request is None:
            return {"error": "invalid_request", "observation": None}
        try:
            observation = await gateway.get_inventory(request.product)
        except InventoryUnavailableError:
            return {"error": "inventory_unavailable", "observation": None}
        return {"observation": observation, "error": None}

    def route_after_lookup(
        state: InventoryState,
    ) -> Literal["sufficient", "insufficient", "manual_review"]:
        observation = state.get("observation")
        request = state.get("request")
        if observation is None or request is None:
            return "manual_review"
        if observation.source == InventorySource.FIXTURE_FALLBACK:
            return "manual_review"
        if observation.inventory >= request.quantity:
            return "sufficient"
        return "insufficient"

    async def sufficient(state: InventoryState) -> InventoryState:
        request = state.get("request")
        observation = state.get("observation")
        if request is None or observation is None:
            raise RuntimeError("Sufficient branch requires request and observation")
        return {
            "decision": InventoryDecision(
                status=InventoryStatus.SUFFICIENT,
                request=request,
                observation=observation,
                can_fulfill=True,
                reason=(
                    f"Observed inventory {observation.inventory} is at least "
                    f"the requested quantity {request.quantity}."
                ),
                required_action=(
                    "Validate the catalog item and reserve stock before promising fulfillment."
                ),
            )
        }

    async def insufficient(state: InventoryState) -> InventoryState:
        request = state.get("request")
        observation = state.get("observation")
        if request is None or observation is None:
            raise RuntimeError("Insufficient branch requires request and observation")
        return {
            "decision": InventoryDecision(
                status=InventoryStatus.INSUFFICIENT,
                request=request,
                observation=observation,
                can_fulfill=False,
                reason=(
                    f"Observed inventory {observation.inventory} is below "
                    f"the requested quantity {request.quantity}."
                ),
                required_action="Offer a smaller quantity, alternative product, or human review.",
            )
        }

    async def manual_review(state: InventoryState) -> InventoryState:
        request = state.get("request")
        observation = state.get("observation")
        if observation is not None and observation.source == InventorySource.FIXTURE_FALLBACK:
            reason = "Only fallback fixture data is available after the live lookup failed."
        elif state.get("error") == "invalid_request":
            reason = "The A2A request did not match the required JSON contract."
        else:
            reason = "No usable live inventory observation is available."
        return {
            "decision": InventoryDecision(
                status=InventoryStatus.MANUAL_REVIEW,
                request=request,
                observation=observation,
                can_fulfill=None,
                reason=reason,
                required_action="Do not authorize fulfillment; obtain a verified inventory observation.",
            )
        }

    async def render_report(state: InventoryState) -> InventoryState:
        decision = state.get("decision")
        if decision is None:
            raise RuntimeError("Inventory graph completed without a decision")

        machine_payload = json.dumps(
            decision.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
        explanation = _deterministic_explanation(decision)
        if model is not None:
            response = await model.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "Explain the supplied inventory decision in at most three sentences. "
                            "Do not change any quantity, status, source, warning, or required action. "
                            "Never claim that inventory has been reserved."
                        )
                    ),
                    HumanMessage(content=machine_payload),
                ]
            )
            model_text = _message_text(response).strip()
            if model_text:
                explanation = model_text

        report = (
            "# Inventory availability decision\n\n"
            "```json\n"
            f"{machine_payload}\n"
            "```\n\n"
            "## Explanation\n"
            f"{explanation}"
        )
        return {"report": report}

    builder = StateGraph(InventoryState)
    builder.add_node("parse_request", parse_request)
    builder.add_node("lookup_inventory", lookup_inventory)
    builder.add_node("sufficient", sufficient)
    builder.add_node("insufficient", insufficient)
    builder.add_node("manual_review", manual_review)
    builder.add_node("render_report", render_report)

    builder.add_edge(START, "parse_request")
    builder.add_conditional_edges(
        "parse_request",
        route_after_parse,
        {
            "lookup_inventory": "lookup_inventory",
            "manual_review": "manual_review",
        },
    )
    builder.add_conditional_edges(
        "lookup_inventory",
        route_after_lookup,
        {
            "sufficient": "sufficient",
            "insufficient": "insufficient",
            "manual_review": "manual_review",
        },
    )
    builder.add_edge("sufficient", "render_report")
    builder.add_edge("insufficient", "render_report")
    builder.add_edge("manual_review", "render_report")
    builder.add_edge("render_report", END)

    resolved_checkpointer = checkpointer if checkpointer is not None else InMemorySaver()
    return builder.compile(checkpointer=resolved_checkpointer, name="inventory-availability-workflow")


def build_live_inventory_graph(
    settings: Settings,
    *,
    credential: TokenCredential | None = None,
) -> InventoryGraph:
    """Build the live graph using the same Microsoft Foundry deployment as MAF."""
    settings.require_foundry()
    resolved_credential = credential or build_credential(settings)
    model = AzureAIOpenAIApiChatModel(
        project_endpoint=settings.foundry_project_endpoint,
        model=settings.foundry_model,
        credential=resolved_credential,
    )
    gateway = InventoryGateway(
        base_url=str(settings.inventory_api_url),
        mode=settings.inventory_mode,
        timeout_seconds=settings.inventory_timeout_seconds,
        max_attempts=settings.inventory_max_attempts,
        retry_delay_seconds=settings.inventory_retry_delay_seconds,
        fallback_to_fixture=settings.inventory_fallback_to_fixture,
    )
    return build_inventory_graph(gateway, model=model)
