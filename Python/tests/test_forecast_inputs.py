import numpy as np
import pandas as pd
import pytest
from fpa_system.forecasting import _fit_predict


@pytest.mark.parametrize(
    "dates,values,future",
    [
        ([], np.array([]), ["2026-01-01"]),
        (["2025-01-01"], np.array([1.0, 2.0]), ["2026-01-01"]),
        (["2025-01-01", "2025-01-15"], np.array([1.0, 2.0]), ["2026-01-01"]),
        (["2025-01-01"], np.array([np.nan]), ["2026-01-01"]),
        (["2025-01-01"], np.array([-1.0]), ["2026-01-01"]),
        (["2025-02-01", "2025-01-01"], np.array([1.0, 2.0]), ["2026-01-01"]),
        (["2025-01-01"], np.array([1.0]), ["2025-01-01"]),
    ],
)
def test_forecast_models_reject_invalid_training_contract(dates, values, future):
    with pytest.raises(ValueError):
        _fit_predict("Seasonal Naive", pd.Series(dates), values, pd.DatetimeIndex(future))


@pytest.mark.parametrize("values", [[100.0, True], [100.0, "120"]])
def test_forecast_rejects_coercible_training_values(values):
    dates = pd.Series(pd.date_range("2025-01-01", periods=2, freq="MS"))
    future = pd.date_range("2025-03-01", periods=1, freq="MS")
    with pytest.raises(ValueError, match="native numeric"):
        _fit_predict("Seasonal Naive", dates, np.array(values, dtype=object), future)
