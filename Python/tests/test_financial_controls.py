import unittest

import numpy as np
import pandas as pd

from fpa_system.config import DATA_DIR


class FinancialControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monthly = pd.read_csv(DATA_DIR / "monthly_pnl.csv")
        cls.cash = pd.read_csv(DATA_DIR / "fact_cash_flow.csv")
        cls.working = pd.read_csv(DATA_DIR / "fact_working_capital.csv")
        cls.scenarios = pd.read_csv(DATA_DIR / "scenario_summary.csv").set_index(
            "Scenario"
        )
        cls.models = pd.read_csv(DATA_DIR / "forecast_model_comparison.csv")

    def test_gross_profit_and_ebitda_reconcile(self):
        self.assertTrue(
            np.allclose(
                self.monthly["GrossProfitTRY"],
                self.monthly["RevenueTRY"] - self.monthly["COGSTRY"],
                atol=1,
            )
        )
        self.assertTrue(
            np.allclose(
                self.monthly["EBITDATRY"],
                self.monthly["GrossProfitTRY"]
                - self.monthly["OperatingExpenseTRY"],
                atol=1,
            )
        )

    def test_cash_roll_forward(self):
        self.assertTrue(
            np.allclose(
                self.cash["EndingCashTRY"],
                self.cash["BeginningCashTRY"] + self.cash["NetCashFlowTRY"],
                atol=1,
            )
        )

    def test_working_capital_reconciles(self):
        self.assertTrue(
            np.allclose(
                self.working["NetWorkingCapitalTRY"],
                self.working["AccountsReceivableTRY"]
                + self.working["InventoryTRY"]
                - self.working["AccountsPayableTRY"],
                atol=1,
            )
        )

    def test_scenario_hierarchy(self):
        self.assertGreater(
            self.scenarios.loc["Upside", "RevenueTRY"],
            self.scenarios.loc["Base", "RevenueTRY"],
        )
        self.assertGreater(
            self.scenarios.loc["Base", "EBITDATRY"],
            self.scenarios.loc["Downside", "EBITDATRY"],
        )
        self.assertGreater(
            self.scenarios.loc["Downside", "EndingCashTRY"],
            self.scenarios.loc["Stress", "EndingCashTRY"],
        )

    def test_one_champion_model_per_business_unit(self):
        champions = self.models[
            self.models["ChampionFlag"].astype(str).str.lower() == "true"
        ]
        self.assertEqual(champions["BusinessUnit"].nunique(), 4)
        self.assertTrue(champions.groupby("BusinessUnit").size().eq(1).all())


if __name__ == "__main__":
    unittest.main()
