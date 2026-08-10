"""Framework-neutral domain logic used by both agents."""

from __future__ import annotations

from enum import StrEnum
from typing import TypedDict


class ControlId(StrEnum):
    """Enterprise controls intentionally kept small for a live demo."""

    GOVERNANCE = "governance"
    DURABILITY = "durability"
    OBSERVABILITY = "observability"
    INTEROPERABILITY = "interoperability"
    SECURITY = "security"


class ControlEvidence(TypedDict):
    control_id: str
    question: str
    acceptance_criteria: list[str]
    warning: str


class RiskResult(TypedDict):
    likelihood: int
    impact: int
    detectability: int
    risk_priority_number: int
    band: str
    action: str


_CONTROLS: dict[ControlId, ControlEvidence] = {
    ControlId.GOVERNANCE: {
        "control_id": ControlId.GOVERNANCE,
        "question": "Where can a human or policy engine stop, approve, or override an agent action?",
        "acceptance_criteria": [
            "High-impact tools have an explicit approval boundary.",
            "The system records who approved the action and when.",
            "Autonomous behavior is bounded by deterministic application rules.",
        ],
        "warning": "A system prompt is guidance, not an authorization boundary.",
    },
    ControlId.DURABILITY: {
        "control_id": ControlId.DURABILITY,
        "question": "Can an interrupted run resume without repeating completed side effects?",
        "acceptance_criteria": [
            "Execution state survives process restart.",
            "External side effects use idempotency keys.",
            "Retry policy distinguishes transient from permanent failure.",
        ],
        "warning": "An in-memory checkpointer demonstrates semantics but is not durable storage.",
    },
    ControlId.OBSERVABILITY: {
        "control_id": ControlId.OBSERVABILITY,
        "question": (
            "Can operators correlate model calls, tool calls, workflow steps, and remote agent tasks?"
        ),
        "acceptance_criteria": [
            "Trace context crosses service and A2A boundaries.",
            "Logs exclude secrets and unnecessary prompt content.",
            "Cost, latency, failure, and retry metrics are available.",
        ],
        "warning": "Logging final answers alone is insufficient for operational diagnosis.",
    },
    ControlId.INTEROPERABILITY: {
        "control_id": ControlId.INTEROPERABILITY,
        "question": (
            "Can independently deployed agents exchange capabilities and task state "
            "through a stable contract?"
        ),
        "acceptance_criteria": [
            "The protocol boundary is versioned.",
            "Agent discovery data is validated as untrusted input.",
            "Timeout, retry, cancellation, and partial failure are handled.",
        ],
        "warning": "Protocol compatibility does not imply shared memory or shared execution semantics.",
    },
    ControlId.SECURITY: {
        "control_id": ControlId.SECURITY,
        "question": "How are identity, authorization, tenant isolation, and untrusted agent output enforced?",
        "acceptance_criteria": [
            "Every remote request is authenticated and authorized.",
            "Task and context identifiers are not treated as bearer credentials.",
            "Remote Agent Cards, messages, and artifacts are sanitized before model use.",
        ],
        "warning": (
            "The demo servers bind to loopback by default and do not implement production authentication."
        ),
    },
}


def lookup_enterprise_control(control_id: str) -> ControlEvidence:
    """Return evidence for one enterprise architecture control."""
    try:
        key = ControlId(control_id.strip().lower())
    except ValueError as exc:
        choices = ", ".join(item.value for item in ControlId)
        raise ValueError(f"Unknown control_id '{control_id}'. Choose one of: {choices}") from exc
    return _CONTROLS[key].copy()


def calculate_operational_risk(likelihood: int, impact: int, detectability: int) -> RiskResult:
    """Calculate a simple 1-5 FMEA-style risk priority number."""
    values = {
        "likelihood": likelihood,
        "impact": impact,
        "detectability": detectability,
    }
    for name, value in values.items():
        if not 1 <= value <= 5:
            raise ValueError(f"{name} must be between 1 and 5; received {value}")

    score = likelihood * impact * detectability
    if score >= 75:
        band, action = "critical", "Block release until mitigations and an accountable owner are recorded."
    elif score >= 40:
        band, action = "high", "Require mitigation, monitoring, and an explicit risk acceptance decision."
    elif score >= 20:
        band, action = "medium", "Track mitigation and verify it before production rollout."
    else:
        band, action = "low", "Accept with routine monitoring."

    return {
        "likelihood": likelihood,
        "impact": impact,
        "detectability": detectability,
        "risk_priority_number": score,
        "band": band,
        "action": action,
    }
