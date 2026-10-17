from __future__ import annotations

import pytest
from fpa_system.scenarios import _validate_scenario_config, run_monte_carlo

VALID_SCENARIO = {
    "Base": {
        "revenue_multiplier": 1.0,
        "cogs_ratio_multiplier": 1.0,
        "opex_multiplier": 1.0,
        "dso_delta": 0,
        "dio_delta": 0,
        "dpo_delta": 0,
    }
}


@pytest.mark.parametrize("iterations", [0, 1, -10])
def test_monte_carlo_rejects_insufficient_iterations(iterations: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        run_monte_carlo(iterations)


@pytest.mark.parametrize("iterations", [True, 2.5, "100"])
def test_monte_carlo_rejects_non_integer_iterations(iterations: object) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        run_monte_carlo(iterations)  # type: ignore[arg-type]


def test_monte_carlo_rejects_resource_exhausting_iteration_count() -> None:
    with pytest.raises(ValueError, match="cannot exceed 1,000,000"):
        run_monte_carlo(1_000_001)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("revenue_multiplier", 0),
        ("cogs_ratio_multiplier", float("nan")),
        ("opex_multiplier", True),
        ("dso_delta", 1.5),
        ("dio_delta", True),
        ("dpo_delta", 366),
    ],
)
def test_scenario_config_rejects_invalid_assumptions(field: str, value: object) -> None:
    scenario = {"Base": {**VALID_SCENARIO["Base"], field: value}}
    with pytest.raises(ValueError, match="Scenario Base"):
        _validate_scenario_config(scenario)


def test_scenario_config_requires_complete_contract() -> None:
    scenario = {"Base": {**VALID_SCENARIO["Base"]}}
    scenario["Base"].pop("dpo_delta")
    with pytest.raises(ValueError, match="complete assumption contract"):
        _validate_scenario_config(scenario)
