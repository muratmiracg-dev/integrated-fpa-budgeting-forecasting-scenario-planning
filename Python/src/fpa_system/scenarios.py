from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ACTUAL_END, DATA_DIR, RANDOM_SEED, SCENARIOS
from .planning import aggregate_pnl


def build_scenarios() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    forecast = pd.read_csv(DATA_DIR / "fact_forecast.csv", parse_dates=["Month"])
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    cost_centers = pd.read_csv(DATA_DIR / "dim_cost_center.csv")
    account_group = accounts.set_index("AccountKey")["AccountGroup"].to_dict()
    future_start = pd.Timestamp(ACTUAL_END) + pd.DateOffset(months=1)
    scenario_rows: list[dict] = []

    for scenario, assumptions in SCENARIOS.items():
        scenario_frame = forecast.copy()
        scenario_frame["Scenario"] = scenario
        future_mask = scenario_frame["Month"] >= future_start
        groups = scenario_frame["AccountKey"].map(account_group)
        revenue_mask = future_mask & groups.eq("Revenue")
        cogs_mask = future_mask & groups.eq("COGS")
        opex_mask = future_mask & groups.eq("Operating Expense")
        scenario_frame.loc[revenue_mask, "AmountTRY"] *= assumptions[
            "revenue_multiplier"
        ]
        scenario_frame.loc[cogs_mask, "AmountTRY"] *= (
            assumptions["revenue_multiplier"]
            * assumptions["cogs_ratio_multiplier"]
        )
        scenario_frame.loc[opex_mask, "AmountTRY"] *= assumptions["opex_multiplier"]
        scenario_frame = scenario_frame[
            ~(
                future_mask
                & scenario_frame["AccountKey"].eq("A6900")
            )
        ].copy()

        for month, month_frame in scenario_frame[
            scenario_frame["Month"] >= future_start
        ].groupby("Month"):
            totals = (
                month_frame.assign(
                    AccountGroup=month_frame["AccountKey"].map(account_group)
                )
                .groupby("AccountGroup")["AmountTRY"]
                .sum()
            )
            ebt = (
                float(totals.get("Revenue", 0))
                - float(totals.get("COGS", 0))
                - float(totals.get("Operating Expense", 0))
                - float(totals.get("Depreciation", 0))
                - float(totals.get("Interest", 0))
            )
            corporate = cost_centers[
                cost_centers["CostCenterID"] == "CC-801"
            ].iloc[0]
            scenario_frame = pd.concat(
                [
                    scenario_frame,
                    pd.DataFrame(
                        [
                            {
                                "Month": month,
                                "CostCenterID": "CC-801",
                                "Department": corporate["Department"],
                                "BusinessUnit": corporate["BusinessUnit"],
                                "Region": corporate["Region"],
                                "Version": "Scenario",
                                "PeriodStatus": "Forecast",
                                "SourceSystem": "Scenario Engine",
                                "AccountKey": "A6900",
                                "AmountTRY": round(max(ebt, 0) * 0.25, 2),
                                "Scenario": scenario,
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )
        scenario_rows.extend(scenario_frame.to_dict("records"))

    fact_scenario = pd.DataFrame(scenario_rows).sort_values(
        ["Scenario", "Month", "CostCenterID", "AccountKey"]
    )
    monthly = aggregate_pnl(
        fact_scenario, accounts, ["Month", "Scenario"]
    ).sort_values(["Scenario", "Month"])

    base_cash = pd.read_csv(DATA_DIR / "fact_cash_flow.csv", parse_dates=["Month"])
    actual_cash = float(
        base_cash[
            (base_cash["Version"] == "Actual")
            & (base_cash["Month"] == pd.Timestamp(ACTUAL_END))
        ]["EndingCashTRY"].iloc[0]
    )
    scenario_summary_rows: list[dict] = []
    scenario_cash_rows: list[dict] = []
    for scenario, frame in monthly.groupby("Scenario"):
        assumptions = SCENARIOS[scenario]
        frame = frame.sort_values("Month")
        working = pd.read_csv(
            DATA_DIR / "fact_working_capital.csv", parse_dates=["Month"]
        )
        base_wc = (
            working[working["Version"] == "Forecast"]
            .set_index("Month")
            .sort_index()
        )
        capex = pd.read_csv(DATA_DIR / "fact_capex.csv", parse_dates=["Month"])
        capex_monthly = (
            capex[capex["Version"] == "Forecast"]
            .groupby("Month")["CapexSpendTRY"]
            .sum()
            .to_dict()
        )
        beginning_cash = actual_cash
        prior_nwc = float(
            working[
                (working["Version"] == "Actual")
                & (working["Month"] == pd.Timestamp(ACTUAL_END))
            ]["NetWorkingCapitalTRY"].iloc[0]
        )
        for _, row in frame.iterrows():
            month = pd.Timestamp(row["Month"])
            if month <= pd.Timestamp(ACTUAL_END):
                continue
            days = month.days_in_month
            base_days = base_wc.loc[month]
            dso = float(base_days["DSO"]) + assumptions["dso_delta"]
            dio = float(base_days["DIO"]) + assumptions["dio_delta"]
            dpo = float(base_days["DPO"]) + assumptions["dpo_delta"]
            nwc = (
                float(row["RevenueTRY"]) * dso / days
                + float(row["COGSTRY"]) * dio / days
                - float(row["COGSTRY"]) * dpo / days
            )
            change_nwc = nwc - prior_nwc
            capex_spend = float(capex_monthly.get(month, 0)) * (
                1.02 if scenario == "Upside" else 0.94 if scenario in ("Downside", "Stress") else 1.0
            )
            cfo = (
                float(row["EBITDATRY"])
                - float(row["TaxTRY"])
                - float(row["InterestTRY"])
                - change_nwc
            )
            financing = -2_000_000 if month.month in (3, 6, 9, 12) else 0
            ending_cash = beginning_cash + cfo - capex_spend + financing
            scenario_cash_rows.append(
                {
                    "Month": month,
                    "Scenario": scenario,
                    "BeginningCashTRY": round(beginning_cash, 2),
                    "CashFromOperationsTRY": round(cfo, 2),
                    "CapitalExpenditureTRY": round(capex_spend, 2),
                    "FinancingCashFlowTRY": round(financing, 2),
                    "EndingCashTRY": round(ending_cash, 2),
                    "DSO": round(dso, 2),
                    "DIO": round(dio, 2),
                    "DPO": round(dpo, 2),
                    "CashConversionCycleDays": round(dso + dio - dpo, 2),
                }
            )
            beginning_cash = ending_cash
            prior_nwc = nwc

        fy2026 = frame[frame["Month"].dt.year == 2026]
        scenario_cash = [
            row
            for row in scenario_cash_rows
            if row["Scenario"] == scenario
            and pd.Timestamp(row["Month"]).year == 2026
        ]
        revenue = float(fy2026["RevenueTRY"].sum())
        gross_profit = float(fy2026["GrossProfitTRY"].sum())
        ebitda = float(fy2026["EBITDATRY"].sum())
        net_income = float(fy2026["NetIncomeTRY"].sum())
        scenario_summary_rows.append(
            {
                "Scenario": scenario,
                "RevenueTRY": round(revenue, 2),
                "GrossProfitTRY": round(gross_profit, 2),
                "EBITDATRY": round(ebitda, 2),
                "NetIncomeTRY": round(net_income, 2),
                "GrossMarginPct": round(gross_profit / revenue, 6),
                "EBITDAMarginPct": round(ebitda / revenue, 6),
                "EndingCashTRY": round(scenario_cash[-1]["EndingCashTRY"], 2),
                "MinimumCashTRY": round(
                    min(row["EndingCashTRY"] for row in scenario_cash), 2
                ),
                "CashConversionCycleDays": round(
                    np.mean(
                        [row["CashConversionCycleDays"] for row in scenario_cash]
                    ),
                    2,
                ),
            }
        )

    scenario_cash = pd.DataFrame(scenario_cash_rows)
    scenario_summary = pd.DataFrame(scenario_summary_rows)
    scenario_order = {"Upside": 1, "Base": 2, "Downside": 3, "Stress": 4}
    scenario_summary["ScenarioOrder"] = scenario_summary["Scenario"].map(
        scenario_order
    )
    scenario_summary = scenario_summary.sort_values("ScenarioOrder")
    fact_scenario.to_csv(
        DATA_DIR / "fact_scenario.csv", index=False, date_format="%Y-%m-%d"
    )
    monthly.to_csv(
        DATA_DIR / "scenario_monthly_pnl.csv",
        index=False,
        date_format="%Y-%m-%d",
    )
    scenario_cash.to_csv(
        DATA_DIR / "scenario_cash_flow.csv",
        index=False,
        date_format="%Y-%m-%d",
    )
    scenario_summary.to_csv(DATA_DIR / "scenario_summary.csv", index=False)
    return fact_scenario, monthly, scenario_summary


def run_monte_carlo(iterations: int = 5000) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_SEED)
    scenario_summary = pd.read_csv(DATA_DIR / "scenario_summary.csv")
    base = scenario_summary[scenario_summary["Scenario"] == "Base"].iloc[0]
    budget_fact = pd.read_csv(DATA_DIR / "fact_budget.csv")
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    budget_pnl = aggregate_pnl(budget_fact, accounts, ["Version"])
    budget_ebitda = float(budget_pnl["EBITDATRY"].iloc[0])
    rows = []
    for iteration in range(1, iterations + 1):
        revenue_multiplier = float(rng.normal(1.0, 0.075))
        gross_margin_delta = float(rng.normal(0.0, 0.018))
        opex_multiplier = float(rng.normal(1.0, 0.045))
        dso_delta = float(rng.normal(0.0, 5.0))
        revenue = float(base["RevenueTRY"]) * revenue_multiplier
        gross_margin = float(base["GrossMarginPct"]) + gross_margin_delta
        gross_profit = revenue * gross_margin
        base_opex = float(base["GrossProfitTRY"]) - float(base["EBITDATRY"])
        ebitda = gross_profit - base_opex * opex_multiplier
        ending_cash = (
            float(base["EndingCashTRY"])
            + (ebitda - float(base["EBITDATRY"])) * 0.68
            - dso_delta * revenue / 365
        )
        rows.append(
            {
                "Iteration": iteration,
                "RevenueMultiplier": round(revenue_multiplier, 6),
                "GrossMarginDelta": round(gross_margin_delta, 6),
                "OpexMultiplier": round(opex_multiplier, 6),
                "DSODelta": round(dso_delta, 4),
                "RevenueTRY": round(revenue, 2),
                "EBITDATRY": round(ebitda, 2),
                "EndingCashTRY": round(ending_cash, 2),
                "EBITDABelowBudgetFlag": ebitda < budget_ebitda,
                "NegativeCashFlag": ending_cash < 0,
            }
        )
    simulations = pd.DataFrame(rows)
    risk_summary = pd.DataFrame(
        [
            ("Revenue P10", simulations["RevenueTRY"].quantile(0.10), "TRY"),
            ("Revenue P50", simulations["RevenueTRY"].quantile(0.50), "TRY"),
            ("Revenue P90", simulations["RevenueTRY"].quantile(0.90), "TRY"),
            ("EBITDA P10", simulations["EBITDATRY"].quantile(0.10), "TRY"),
            ("EBITDA P50", simulations["EBITDATRY"].quantile(0.50), "TRY"),
            ("EBITDA P90", simulations["EBITDATRY"].quantile(0.90), "TRY"),
            (
                "Probability EBITDA Below Budget",
                simulations["EBITDABelowBudgetFlag"].mean(),
                "Percent",
            ),
            (
                "Probability Negative Cash",
                simulations["NegativeCashFlag"].mean(),
                "Percent",
            ),
            ("Ending Cash P10", simulations["EndingCashTRY"].quantile(0.10), "TRY"),
        ],
        columns=["RiskMetric", "Value", "Unit"],
    )
    simulations.to_csv(DATA_DIR / "monte_carlo_simulations.csv", index=False)
    risk_summary.to_csv(DATA_DIR / "risk_summary.csv", index=False)
    return simulations, risk_summary


if __name__ == "__main__":
    fact, monthly, summary = build_scenarios()
    simulations, risk = run_monte_carlo()
    print(f"fact_scenario: {len(fact):,} rows")
    print(f"scenario_monthly_pnl: {len(monthly):,} rows")
    print(summary.to_string(index=False))
    print(f"monte_carlo_simulations: {len(simulations):,} rows")
