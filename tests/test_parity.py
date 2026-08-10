from __future__ import annotations

from typing import Any

from agent_duet.langgraph.tools import LANGGRAPH_TOOLS
from agent_duet.maf.tools import MAF_TOOLS
from agent_duet.prompts import LANGGRAPH_SYSTEM_PROMPT, MAF_SYSTEM_PROMPT


def _without_titles(value: Any) -> Any:
    """Remove Pydantic model titles that differ only by adapter naming."""
    if isinstance(value, dict):
        return {key: _without_titles(item) for key, item in value.items() if key != "title"}
    if isinstance(value, list):
        return [_without_titles(item) for item in value]
    return value


def _normalize_parameters(schema: dict[str, Any]) -> dict[str, Any]:
    """Compare argument schemas without adapter-only root metadata."""
    normalized = _without_titles(schema)
    if not isinstance(normalized, dict):
        raise AssertionError("Expected a JSON Schema object")
    normalized.pop("description", None)
    return normalized


def test_frameworks_publish_the_same_tool_names() -> None:
    maf_names = {tool.name for tool in MAF_TOOLS}
    langgraph_names = {tool.name for tool in LANGGRAPH_TOOLS}

    assert (
        maf_names
        == langgraph_names
        == {
            "lookup_enterprise_control",
            "calculate_operational_risk",
        }
    )


def test_frameworks_publish_equivalent_function_schemas() -> None:
    maf_contracts: dict[str, dict[str, Any]] = {}
    for tool in MAF_TOOLS:
        function = tool.to_json_schema_spec()["function"]
        maf_contracts[tool.name] = {
            "description": function["description"],
            "parameters": _normalize_parameters(function["parameters"]),
        }

    langgraph_contracts: dict[str, dict[str, Any]] = {}
    for tool in LANGGRAPH_TOOLS:
        langgraph_contracts[tool.name] = {
            "description": tool.description,
            "parameters": _normalize_parameters(tool.get_input_jsonschema()),
        }

    assert maf_contracts == langgraph_contracts


def test_prompts_share_the_same_output_contract() -> None:
    headings = [
        "## Verdict",
        "## Evidence",
        "## Material risks",
        "## Required controls",
        "## Open questions",
    ]

    for heading in headings:
        assert heading in MAF_SYSTEM_PROMPT
        assert heading in LANGGRAPH_SYSTEM_PROMPT
