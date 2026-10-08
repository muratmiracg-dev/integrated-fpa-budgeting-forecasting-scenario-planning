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
