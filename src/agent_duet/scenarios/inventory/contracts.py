"""Typed contracts for the inventory A2A scenario."""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InventorySource(StrEnum):
    """Where an observation originated."""

    LIVE = "live"
    FIXTURE = "fixture"
    FIXTURE_FALLBACK = "fixture-fallback"


class InventoryStatus(StrEnum):
    """Deterministic availability decision made by the LangGraph workflow."""

    SUFFICIENT = "sufficient"
    INSUFFICIENT = "insufficient"
    MANUAL_REVIEW = "manual_review"


class InventoryRequest(BaseModel):
    """The strict payload the MAF orchestrator sends to the remote A2A agent."""

    model_config = ConfigDict(extra="forbid")

    product: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=10_000)

    @field_validator("product")
    @classmethod
    def normalize_product(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("product cannot be blank")
        return normalized


class InventoryAPIResponse(BaseModel):
    """Validated shape returned by the external demo API."""

    model_config = ConfigDict(extra="ignore")

    inventory: int = Field(ge=0)
    prod: str = Field(min_length=1, max_length=100)


class InventoryObservation(BaseModel):
    """One immutable-by-convention stock observation."""

    observation_id: str
    product: str
    inventory: int = Field(ge=0)
    observed_at: datetime
    source: InventorySource
    catalog_verified: bool = False
    warning: str | None = None


class InventoryDecision(BaseModel):
    """Machine-readable decision returned as part of the A2A artifact."""

    status: InventoryStatus
    request: InventoryRequest | None
    observation: InventoryObservation | None
    can_fulfill: bool | None
    reason: str
    required_action: str


def parse_inventory_request(text: str) -> InventoryRequest:
    """Parse the exact JSON contract expected at the A2A boundary."""
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Inventory request must be a JSON object")
    return InventoryRequest.model_validate(payload)
