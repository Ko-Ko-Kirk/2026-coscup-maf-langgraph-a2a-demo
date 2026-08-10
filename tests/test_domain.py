from __future__ import annotations

import pytest

from agent_duet.domain import calculate_operational_risk, lookup_enterprise_control


def test_lookup_control_returns_evidence_without_a_model() -> None:
    result = lookup_enterprise_control("security")

    assert result["control_id"] == "security"
    assert "authenticated and authorized" in result["acceptance_criteria"][0]


def test_lookup_control_rejects_unknown_control() -> None:
    with pytest.raises(ValueError, match="Unknown control_id"):
        lookup_enterprise_control("marketing")


@pytest.mark.parametrize(
    ("values", "expected_band"),
    [
        ((1, 1, 1), "low"),
        ((3, 3, 3), "medium"),
        ((4, 4, 3), "high"),
        ((5, 5, 3), "critical"),
    ],
)
def test_risk_band_is_deterministic(values: tuple[int, int, int], expected_band: str) -> None:
    result = calculate_operational_risk(*values)

    assert result["risk_priority_number"] == values[0] * values[1] * values[2]
    assert result["band"] == expected_band


def test_risk_values_are_bounded() -> None:
    with pytest.raises(ValueError, match="likelihood must be between 1 and 5"):
        calculate_operational_risk(0, 5, 5)
