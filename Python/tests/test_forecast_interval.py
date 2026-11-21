import math
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from fpa_system.forecasting import interval_scale

DATA = Path(__file__).resolve().parents[2] / "Data"


class ForecastIntervalTests(unittest.TestCase):
    def test_constant_bias_widens_the_band(self):
        # Every month over-forecast by 10: the error spread is zero, the error is not.
        actual = np.array([100.0, 110.0, 120.0, 130.0])
        self.assertAlmostEqual(interval_scale(actual, actual + 10), 10.0)

    def test_rmse_combines_bias_and_spread(self):
        actual = np.array([100.0, 100.0, 100.0, 100.0])
        predicted = np.array([103.0, 107.0, 103.0, 107.0])  # bias 5, spread 2
        self.assertAlmostEqual(interval_scale(actual, predicted), math.sqrt(5**2 + 2**2))

    def test_rejects_invalid_inputs(self):
        for actual, predicted in (([], []), ([1, 2], [1]), ([np.nan], [1]), ([[1]], [[1]])):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                interval_scale(np.array(actual, dtype=float), np.array(predicted, dtype=float))

    def test_committed_bands_use_champion_backtest_rmse(self):
        forecast = pd.read_csv(DATA / "revenue_forecast.csv")
        backtest = pd.read_csv(DATA / "forecast_backtest.csv")
        for (unit, model), rows in forecast.groupby(["BusinessUnit", "ChampionModel"]):
            errors = backtest.loc[
                (backtest["BusinessUnit"] == unit) & (backtest["Model"] == model),
                ["ActualRevenueTRY", "PredictedRevenueTRY"],
            ]
            rmse = math.sqrt(
                ((errors["ActualRevenueTRY"] - errors["PredictedRevenueTRY"]) ** 2).mean()
            )
            with self.subTest(unit=unit):
                self.assertEqual(rows["BacktestRMSETRY"].nunique(), 1)
                self.assertAlmostEqual(rows["BacktestRMSETRY"].iloc[0], rmse, delta=0.02)
                first = rows.loc[rows["ForecastHorizonMonth"] == 1].iloc[0]
                half_width = first["Upper80RevenueTRY"] - first["ForecastRevenueTRY"]
                self.assertAlmostEqual(
                    half_width, 1.28 * rmse * math.sqrt(1 + 1 / 24), delta=0.05
                )


if __name__ == "__main__":
    unittest.main()
