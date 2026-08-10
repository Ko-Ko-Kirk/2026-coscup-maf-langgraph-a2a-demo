"""LangChain tool adapters over the framework-neutral domain tools."""

from __future__ import annotations

from typing import Annotated

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from agent_duet.domain import (
    ControlEvidence,
    RiskResult,
)
from agent_duet.domain import (
    calculate_operational_risk as calculate_risk,
)
from agent_duet.domain import (
    lookup_enterprise_control as lookup_control,
)


@tool
def lookup_enterprise_control(
    control_id: Annotated[
        str,
        Field(description=("One of governance, durability, observability, interoperability, or security.")),
    ],
) -> ControlEvidence:
    """Look up the acceptance criteria and warning for one enterprise control."""
    return lookup_control(control_id)


@tool
def calculate_operational_risk(
    likelihood: Annotated[int, Field(ge=1, le=5, description="Probability from 1 (rare) to 5 (likely).")],
    impact: Annotated[int, Field(ge=1, le=5, description="Business impact from 1 to 5.")],
    detectability: Annotated[
        int,
        Field(ge=1, le=5, description="Difficulty of detecting the failure from 1 to 5."),
    ],
) -> RiskResult:
    """Calculate a deterministic FMEA-style risk priority number."""
    return calculate_risk(likelihood, impact, detectability)


LANGGRAPH_TOOLS: list[BaseTool] = [
    lookup_enterprise_control,
    calculate_operational_risk,
]
