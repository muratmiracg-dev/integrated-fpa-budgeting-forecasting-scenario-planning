"""P&L cascade and budget-variance logic, plus consistency of the committed outputs."""

import unittest

import numpy as np
import pandas as pd
from fpa_system.config import DATA_DIR
from fpa_system.planning import aggregate_pnl
from fpa_system.reporting import LINE_ITEMS, _variance_analysis

ACCOUNTS = pd.DataFrame(
    {
        "AccountKey": ["REV", "COGS", "OPEX", "DEP", "INT", "TAX"],
        "AccountGroup": [
            "Revenue",
            "COGS",
            "Operating Expense",
            "Depreciation",
            "Interest",
            "Tax",
        ],
    }
)
AMOUNTS = {"REV": 1_000.0, "COGS": 400.0, "OPEX": 300.0, "DEP": 50.0, "INT": 20.0, "TAX": 46.0}


def fact(amounts, unit="BU1"):
    return pd.DataFrame(
        {"BusinessUnit": unit, "AccountKey": list(amounts), "AmountTRY": list(amounts.values())}
    )


class PnlCascadeTests(unittest.TestCase):
    def test_cascade_and_margins_follow_known_answer(self):
        row = aggregate_pnl(fact(AMOUNTS), ACCOUNTS, ["BusinessUnit"]).iloc[0]
        self.assertEqual(row["GrossProfitTRY"], 600.0)
        self.assertEqual(row["EBITDATRY"], 300.0)
        self.assertEqual(row["EBITTRY"], 250.0)
        self.assertEqual(row["EBTTRY"], 230.0)
        self.assertEqual(row["NetIncomeTRY"], 184.0)
        self.assertAlmostEqual(row["GrossMarginPct"], 0.60)
        self.assertAlmostEqual(row["EBITDAMarginPct"], 0.30)
        self.assertAlmostEqual(row["NetIncomeMarginPct"], 0.184)

    def test_lines_are_summed_per_group_and_missing_groups_are_zero(self):
        frame = pd.concat(
            [
                fact({"REV": 600.0, "COGS": 100.0}),
                fact({"REV": 400.0}),
                fact({"REV": 200.0, "OPEX": 80.0}, unit="BU2"),
            ]
        )
        result = aggregate_pnl(frame, ACCOUNTS, ["BusinessUnit"]).set_index("BusinessUnit")
        self.assertEqual(result.loc["BU1", "RevenueTRY"], 1_000.0)
        self.assertEqual(result.loc["BU1", "EBITDATRY"], 900.0)
        self.assertEqual(result.loc["BU2", "COGSTRY"], 0.0)
        self.assertEqual(result.loc["BU2", "TaxTRY"], 0.0)
        self.assertEqual(result.loc["BU2", "NetIncomeTRY"], 120.0)

    def test_zero_revenue_gives_undefined_margins_not_infinity(self):
        row = aggregate_pnl(fact({"REV": 0.0, "OPEX": 10.0}), ACCOUNTS, ["BusinessUnit"]).iloc[0]
        self.assertEqual(row["EBITDATRY"], -10.0)
        self.assertTrue(np.isnan(row["GrossMarginPct"]))
        self.assertTrue(np.isnan(row["NetIncomeMarginPct"]))


def monthly_frame(budget, actual):
    """One H1-2026 month per version; LINE_ITEMS columns filled from dicts."""
    rows = []
    for version, values in (("Budget", budget), ("Actual", actual)):
        row = {"Month": pd.Timestamp("2026-03-01"), "Year": 2026, "Version": version}
        row.update({column: values.get(column, 0.0) for _, column, _, _ in LINE_ITEMS})
        rows.append(row)
    return pd.DataFrame(rows)


class VarianceDirectionTests(unittest.TestCase):
    def variance(self, budget, actual):
        result = _variance_analysis(monthly_frame(budget, actual))
        h1 = result[result["Comparison"] == "H1 2026 Actual vs Budget"]
        return h1.set_index("Metric")

    def test_revenue_above_budget_is_favorable_and_cost_above_budget_is_not(self):
        result = self.variance(
            {"RevenueTRY": 100.0, "COGSTRY": 40.0}, {"RevenueTRY": 110.0, "COGSTRY": 50.0}
        )
        self.assertEqual(result.loc["Revenue", "VarianceTRY"], 10.0)
        self.assertAlmostEqual(result.loc["Revenue", "VariancePct"], 0.10)
        self.assertEqual(result.loc["Revenue", "Status"], "Favorable")
        self.assertEqual(result.loc["COGS", "VarianceTRY"], 10.0)
        self.assertEqual(result.loc["COGS", "Status"], "Unfavorable")

    def test_revenue_shortfall_and_cost_saving(self):
        result = self.variance(
            {"RevenueTRY": 100.0, "OperatingExpenseTRY": 30.0},
            {"RevenueTRY": 90.0, "OperatingExpenseTRY": 25.0},
        )
        self.assertEqual(result.loc["Revenue", "Status"], "Unfavorable")
        self.assertEqual(result.loc["Operating Expense", "Status"], "Favorable")

    def test_negative_comparator_uses_absolute_base_for_percentage(self):
        result = self.variance({"NetIncomeTRY": -50.0}, {"NetIncomeTRY": -25.0})
        self.assertAlmostEqual(result.loc["Net Income", "VariancePct"], 0.5)
        self.assertEqual(result.loc["Net Income", "Status"], "Favorable")

    def test_zero_comparator_has_undefined_percentage(self):
        result = self.variance({"InterestTRY": 0.0}, {"InterestTRY": 5.0})
        self.assertTrue(np.isnan(result.loc["Interest", "VariancePct"]))
        self.assertEqual(result.loc["Interest", "Status"], "Unfavorable")


class CommittedOutputConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.monthly = pd.read_csv(DATA_DIR / "monthly_pnl.csv", parse_dates=["Month"])
        cls.variance = pd.read_csv(DATA_DIR / "variance_analysis.csv")

    def test_monthly_pnl_satisfies_cascade_identities(self):
        m = self.monthly
        identities = {
            "GrossProfitTRY": m["RevenueTRY"] - m["COGSTRY"],
            "EBITDATRY": m["GrossProfitTRY"] - m["OperatingExpenseTRY"],
            "EBITTRY": m["EBITDATRY"] - m["DepreciationTRY"],
            "EBTTRY": m["EBITTRY"] - m["InterestTRY"],
            "NetIncomeTRY": m["EBTTRY"] - m["TaxTRY"],
        }
        for column, expected in identities.items():
            with self.subTest(column=column):
                np.testing.assert_allclose(m[column], expected, rtol=0, atol=0.01)

    def test_committed_variance_table_matches_reporting_logic(self):
        recomputed = _variance_analysis(self.monthly)
        key = ["Comparison", "Metric"]
        merged = self.variance.merge(recomputed, on=key, suffixes=("", "_new"), validate="1:1")
        self.assertEqual(len(merged), len(self.variance))
        for column in ("CurrentValueTRY", "ComparatorValueTRY", "VarianceTRY"):
            with self.subTest(column=column):
                np.testing.assert_allclose(merged[column], merged[f"{column}_new"], atol=0.01)
        self.assertTrue((merged["Status"] == merged["Status_new"]).all())

    def test_committed_status_agrees_with_sign_and_direction(self):
        direction = {metric: higher for metric, _, _, higher in LINE_ITEMS}
        for row in self.variance.itertuples():
            favorable = row.VarianceTRY >= 0 if direction[row.Metric] else row.VarianceTRY <= 0
            with self.subTest(comparison=row.Comparison, metric=row.Metric):
                self.assertEqual(row.Status, "Favorable" if favorable else "Unfavorable")


if __name__ == "__main__":
    unittest.main()
