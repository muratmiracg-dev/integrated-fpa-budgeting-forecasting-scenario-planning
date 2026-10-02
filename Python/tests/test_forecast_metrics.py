import unittest

import numpy as np
from fpa_system.forecasting import _metrics


class ForecastMetricTests(unittest.TestCase):
    def test_ratios_are_invariant_to_revenue_units(self):
        for scale in (1.0, 0.001):
            with self.subTest(scale=scale):
                metrics = _metrics(np.array([1.0, 2.0]) * scale, np.array([2.0, 3.0]) * scale)
                self.assertAlmostEqual(metrics["WAPE"], 2 / 3)
                self.assertAlmostEqual(metrics["Bias"], 2 / 3)

    def test_zero_revenue_retains_overprediction_penalty(self):
        self.assertEqual(_metrics(np.zeros(2), np.array([2.0, 1.0]))["WAPE"], 3.0)
        self.assertEqual(_metrics(np.zeros(2), np.zeros(2))["Score"], 0.0)

    def test_rejects_invalid_metric_inputs(self):
        for actual, predicted in (
            ([], []),
            ([1, 2], [1]),
            ([[1]], [[1]]),
            ([np.nan], [1]),
            ([1], [np.inf]),
            ([-1], [1]),
            ([1], [-1]),
        ):
            with self.subTest(actual=actual, predicted=predicted):
                with self.assertRaises(ValueError):
                    _metrics(actual, predicted)
