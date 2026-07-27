from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import ACTUAL_END, ACTUAL_START, DATA_DIR


def validate_project(report_path: Path | None = None) -> dict:
    checks: list[dict] = []

    def add_check(name: str, passed: bool, detail: str, category: str) -> None:
        checks.append(
            {
                "check": name,
                "passed": bool(passed),
                "detail": detail,
                "category": category,
            }
        )

    actuals = pd.read_csv(DATA_DIR / "fact_actuals.csv", parse_dates=["Month"])
    budget = pd.read_csv(DATA_DIR / "fact_budget.csv", parse_dates=["Month"])
    forecast = pd.read_csv(DATA_DIR / "fact_forecast.csv", parse_dates=["Month"])
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    cost_centers = pd.read_csv(DATA_DIR / "dim_cost_center.csv")
    monthly = pd.read_csv(DATA_DIR / "monthly_pnl.csv", parse_dates=["Month"])
    working = pd.read_csv(
        DATA_DIR / "fact_working_capital.csv", parse_dates=["Month"]
    )
    cash = pd.read_csv(DATA_DIR / "fact_cash_flow.csv", parse_dates=["Month"])
    scenarios = pd.read_csv(DATA_DIR / "scenario_summary.csv")
    models = pd.read_csv(DATA_DIR / "forecast_model_comparison.csv")
    submissions = pd.read_csv(DATA_DIR / "budget_submissions.csv")
    monte_carlo = pd.read_csv(DATA_DIR / "monte_carlo_simulations.csv")
    capex = pd.read_csv(DATA_DIR / "fact_capex.csv")

    add_check(
        "Actual month coverage",
        actuals["Month"].min() == pd.Timestamp(ACTUAL_START)
        and actuals["Month"].max() == pd.Timestamp(ACTUAL_END)
        and actuals["Month"].nunique() == 42,
        f"{actuals['Month'].min().date()} to {actuals['Month'].max().date()} / {actuals['Month'].nunique()} months",
        "Coverage",
    )
    add_check(
        "Budget month coverage",
        budget["Month"].nunique() == 12
        and budget["Month"].min() == pd.Timestamp("2026-01-01")
        and budget["Month"].max() == pd.Timestamp("2026-12-01"),
        f"{budget['Month'].nunique()} FY2026 months",
        "Coverage",
    )
    add_check(
        "Rolling forecast coverage",
        forecast["Month"].nunique() == 18
        and forecast["Month"].min() == pd.Timestamp("2026-01-01")
        and forecast["Month"].max() == pd.Timestamp("2027-06-01"),
        f"{forecast['Month'].nunique()} months ending {forecast['Month'].max().date()}",
        "Coverage",
    )
    add_check(
        "Account foreign keys",
        set(actuals["AccountKey"]).issubset(set(accounts["AccountKey"]))
        and set(budget["AccountKey"]).issubset(set(accounts["AccountKey"]))
        and set(forecast["AccountKey"]).issubset(set(accounts["AccountKey"])),
        "All account keys resolve to the chart of accounts",
        "Referential integrity",
    )
    add_check(
        "Cost center foreign keys",
        set(actuals["CostCenterID"]).issubset(set(cost_centers["CostCenterID"]))
        and set(budget["CostCenterID"]).issubset(set(cost_centers["CostCenterID"]))
        and set(forecast["CostCenterID"]).issubset(set(cost_centers["CostCenterID"])),
        "All cost-center keys resolve",
        "Referential integrity",
    )
    add_check(
        "Non-negative ledger amounts",
        bool(
            (actuals["AmountTRY"] >= 0).all()
            and (budget["AmountTRY"] >= 0).all()
            and (forecast["AmountTRY"] >= 0).all()
        ),
        "Natural-sign storage uses non-negative amounts",
        "Financial integrity",
    )
    pnl_identity = np.allclose(
        monthly["GrossProfitTRY"],
        monthly["RevenueTRY"] - monthly["COGSTRY"],
        atol=1,
    ) and np.allclose(
        monthly["EBITDATRY"],
        monthly["GrossProfitTRY"] - monthly["OperatingExpenseTRY"],
        atol=1,
    )
    add_check(
        "P&L identities",
        pnl_identity,
        "Gross profit and EBITDA reconcile on every monthly row",
        "Financial integrity",
    )
    net_income_identity = np.allclose(
        monthly["NetIncomeTRY"],
        monthly["EBITDATRY"]
        - monthly["DepreciationTRY"]
        - monthly["InterestTRY"]
        - monthly["TaxTRY"],
        atol=1,
    )
    add_check(
        "Net income identity",
        net_income_identity,
        "Net income reconciles to EBITDA, D&A, interest and tax",
        "Financial integrity",
    )
    cash_sorted = cash.sort_values(["Version", "Month"])
    cash_identity = np.allclose(
        cash_sorted["EndingCashTRY"],
        cash_sorted["BeginningCashTRY"] + cash_sorted["NetCashFlowTRY"],
        atol=1,
    )
    add_check(
        "Cash roll-forward",
        cash_identity,
        "Ending cash equals beginning cash plus net cash flow",
        "Financial integrity",
    )
    wc_identity = np.allclose(
        working["NetWorkingCapitalTRY"],
        working["AccountsReceivableTRY"]
        + working["InventoryTRY"]
        - working["AccountsPayableTRY"],
        atol=1,
    )
    add_check(
        "Working capital identity",
        wc_identity,
        "NWC equals AR plus inventory less AP",
        "Financial integrity",
    )
    scenario_lookup = scenarios.set_index("Scenario")
    add_check(
        "Scenario revenue ordering",
        scenario_lookup.loc["Upside", "RevenueTRY"]
        > scenario_lookup.loc["Base", "RevenueTRY"]
        > scenario_lookup.loc["Downside", "RevenueTRY"]
        > scenario_lookup.loc["Stress", "RevenueTRY"],
        "Upside > Base > Downside > Stress",
        "Scenario engine",
    )
    add_check(
        "Scenario EBITDA ordering",
        scenario_lookup.loc["Upside", "EBITDATRY"]
        > scenario_lookup.loc["Base", "EBITDATRY"]
        > scenario_lookup.loc["Downside", "EBITDATRY"]
        > scenario_lookup.loc["Stress", "EBITDATRY"],
        "EBITDA follows the expected scenario hierarchy",
        "Scenario engine",
    )
    champions = models[models["ChampionFlag"].astype(str).str.lower() == "true"]
    add_check(
        "One champion forecast model per business unit",
        champions.groupby("BusinessUnit").size().eq(1).all()
        and champions["BusinessUnit"].nunique() == 4,
        f"{champions['BusinessUnit'].nunique()} business-unit champions",
        "Forecasting",
    )
    add_check(
        "Forecast accuracy threshold",
        bool((champions["WAPE"] < 0.08).all()),
        f"Champion WAPE range {champions['WAPE'].min():.2%} to {champions['WAPE'].max():.2%}",
        "Forecasting",
    )
    add_check(
        "Budget governance complete",
        submissions["Status"].str.startswith("Approved").all()
        and submissions["CostCenterID"].nunique() == 12,
        "All 12 budget-owner submissions are approved",
        "Governance",
    )
    add_check(
        "Capex schedule non-negative",
        bool(
            (
                capex[
                    ["CapexSpendTRY", "DepreciationTRY", "RemainingNBVTRY"]
                ]
                >= 0
            )
            .all()
            .all()
        ),
        "No negative spend, depreciation or NBV values",
        "Capex",
    )
    add_check(
        "Monte Carlo simulation count",
        len(monte_carlo) == 5000
        and np.isfinite(
            monte_carlo[["RevenueTRY", "EBITDATRY", "EndingCashTRY"]].to_numpy()
        ).all(),
        f"{len(monte_carlo):,} finite simulation rows",
        "Risk analytics",
    )

    report = {
        "project": "Integrated FP&A Budgeting, Forecasting & Scenario Planning System",
        "all_passed": all(check["passed"] for check in checks),
        "passed_checks": sum(check["passed"] for check in checks),
        "total_checks": len(checks),
        "checks": checks,
    }
    report_path = report_path or DATA_DIR / "validation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = validate_project()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["all_passed"] else 1)
