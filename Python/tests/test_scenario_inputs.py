from __future__ import annotations

import pytest
from fpa_system.scenarios import run_monte_carlo


@pytest.mark.parametrize("iterations", [0, 1, -10])
def test_monte_carlo_rejects_insufficient_iterations(iterations: int) -> None:
    with pytest.raises(ValueError, match="at least 2"):
        run_monte_carlo(iterations)


@pytest.mark.parametrize("iterations", [True, 2.5, "100"])
def test_monte_carlo_rejects_non_integer_iterations(iterations: object) -> None:
    with pytest.raises(TypeError, match="must be an integer"):
        run_monte_carlo(iterations)  # type: ignore[arg-type]
