from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ACTUAL_END, AS_OF_DATE, COMPANY_NAME, DATA_DIR
from .planning import aggregate_pnl


LINE_ITEMS = [
    ("Revenue", "RevenueTRY", 1, True),
    ("COGS", "COGSTRY", 2, False),
    ("Gross Profit", "GrossProfitTRY", 3, True),
    ("Operating Expense", "OperatingExpenseTRY", 4, False),
    ("EBITDA", "EBITDATRY", 5, True),
    ("Depreciation", "DepreciationTRY", 6, False),
    ("EBIT", "EBITTRY", 7, True),
    ("Interest", "InterestTRY", 8, False),
    ("Tax", "TaxTRY", 9, False),
    ("Net Income", "NetIncomeTRY", 10, True),
]


def _monthly_pnl() -> pd.DataFrame:
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    facts = {
        "Actual": pd.read_csv(DATA_DIR / "fact_actuals.csv", parse_dates=["Month"]),
        "Budget": pd.read_csv(DATA_DIR / "fact_budget.csv", parse_dates=["Month"]),
        "Forecast": pd.read_csv(DATA_DIR / "fact_forecast.csv", parse_dates=["Month"]),
    }
    rows = []
    for version, fact in facts.items():
        pnl = aggregate_pnl(fact, accounts, ["Month"])
        pnl["Version"] = version
        pnl["PeriodStatus"] = np.where(
            (version == "Actual")
            | ((version == "Forecast") & (pnl["Month"] <= pd.Timestamp(ACTUAL_END))),
            "Actual",
            version,
        )
        rows.append(pnl)
    monthly = pd.concat(rows, ignore_index=True)
    monthly["MonthKey"] = monthly["Month"].dt.strftime("%Y-%m")
    monthly["MonthLabel"] = monthly["Month"].dt.strftime("%b %Y")
    monthly["Year"] = monthly["Month"].dt.year
    monthly["Quarter"] = "Q" + monthly["Month"].dt.quarter.astype(str)
    monthly["RevenueGrowthPct"] = (
        monthly.sort_values("Month")
        .groupby("Version")["RevenueTRY"]
        .pct_change(12)
    )
    monthly["ForecastAccuracyPct"] = np.nan
    actual_lookup = monthly[monthly["Version"] == "Actual"].set_index("Month")[
        "RevenueTRY"
    ].to_dict()
    for idx, row in monthly[monthly["Version"] == "Forecast"].iterrows():
        actual = actual_lookup.get(row["Month"])
        if actual:
            monthly.at[idx, "ForecastAccuracyPct"] = 1 - abs(
                row["RevenueTRY"] - actual
            ) / actual
    return monthly.sort_values(["Version", "Month"])


def _annual_pnl(monthly: pd.DataFrame) -> pd.DataFrame:
    amount_columns = [
        "RevenueTRY",
        "COGSTRY",
        "GrossProfitTRY",
        "OperatingExpenseTRY",
        "EBITDATRY",
        "DepreciationTRY",
        "EBITTRY",
        "InterestTRY",
        "EBTTRY",
        "TaxTRY",
        "NetIncomeTRY",
    ]
    annual = (
        monthly.groupby(["Year", "Version"], as_index=False)[amount_columns]
        .sum()
        .sort_values(["Year", "Version"])
    )
    annual["GrossMarginPct"] = annual["GrossProfitTRY"] / annual["RevenueTRY"]
    annual["EBITDAMarginPct"] = annual["EBITDATRY"] / annual["RevenueTRY"]
    annual["NetIncomeMarginPct"] = annual["NetIncomeTRY"] / annual["RevenueTRY"]
    annual["MonthsIncluded"] = annual.apply(
        lambda row: int(
            monthly[
                (monthly["Year"] == row["Year"])
                & (monthly["Version"] == row["Version"])
            ]["Month"].nunique()
        ),
        axis=1,
    )
    return annual


def _variance_analysis(monthly: pd.DataFrame) -> pd.DataFrame:
    comparisons = [
        (
            "H1 2026 Actual vs Budget",
            monthly[
                (monthly["Version"] == "Actual")
                & (monthly["Month"].between("2026-01-01", ACTUAL_END))
            ],
            monthly[
                (monthly["Version"] == "Budget")
                & (monthly["Month"].between("2026-01-01", ACTUAL_END))
            ],
            "Actual",
            "Budget",
        ),
        (
            "FY2026 Forecast vs Budget",
            monthly[
                (monthly["Version"] == "Forecast") & (monthly["Year"] == 2026)
            ],
            monthly[
                (monthly["Version"] == "Budget") & (monthly["Year"] == 2026)
            ],
            "Forecast",
            "Budget",
        ),
        (
            "FY2025 Actual vs FY2024 Actual",
            monthly[
                (monthly["Version"] == "Actual") & (monthly["Year"] == 2025)
            ],
            monthly[
                (monthly["Version"] == "Actual") & (monthly["Year"] == 2024)
            ],
            "FY2025 Actual",
            "FY2024 Actual",
        ),
    ]
    rows: list[dict] = []
    for comparison, current, comparator, current_label, comparator_label in comparisons:
        for metric, column, order, higher_is_better in LINE_ITEMS:
            current_value = float(current[column].sum())
            comparator_value = float(comparator[column].sum())
            variance = current_value - comparator_value
            variance_pct = variance / abs(comparator_value) if comparator_value else np.nan
            favorable = variance >= 0 if higher_is_better else variance <= 0
            rows.append(
                {
                    "Comparison": comparison,
                    "Metric": metric,
                    "MetricOrder": order,
                    "CurrentLabel": current_label,
                    "ComparatorLabel": comparator_label,
                    "CurrentValueTRY": round(current_value, 2),
                    "ComparatorValueTRY": round(comparator_value, 2),
                    "VarianceTRY": round(variance, 2),
                    "VariancePct": round(variance_pct, 6),
                    "FavorableFlag": favorable,
                    "Status": "Favorable" if favorable else "Unfavorable",
                }
            )
    return pd.DataFrame(rows)


def _performance_by_dimension(
    dimension: str, filename: str
) -> pd.DataFrame:
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    facts = {
        "Actual": pd.read_csv(DATA_DIR / "fact_actuals.csv", parse_dates=["Month"]),
        "Budget": pd.read_csv(DATA_DIR / "fact_budget.csv", parse_dates=["Month"]),
        "Forecast": pd.read_csv(DATA_DIR / "fact_forecast.csv", parse_dates=["Month"]),
    }
    rows = []
    for version, fact in facts.items():
        pnl = aggregate_pnl(fact, accounts, ["Month", dimension])
        pnl["Version"] = version
        rows.append(pnl)
    result = pd.concat(rows, ignore_index=True)
    result["Year"] = result["Month"].dt.year
    result["MonthKey"] = result["Month"].dt.strftime("%Y-%m")
    result.to_csv(DATA_DIR / filename, index=False, date_format="%Y-%m-%d")
    return result


def _headcount_summary() -> pd.DataFrame:
    headcount = pd.read_csv(DATA_DIR / "fact_headcount.csv", parse_dates=["Month"])
    return (
        headcount.groupby(["Month", "Version", "Department"], as_index=False)
        .agg(
            FTE=("FTE", "sum"),
            Hires=("Hires", "sum"),
            Exits=("Exits", "sum"),
            PayrollCostTRY=("PayrollCostTRY", "sum"),
            BenefitsCostTRY=("BenefitsCostTRY", "sum"),
        )
        .sort_values(["Version", "Month", "Department"])
    )


def _capex_summary() -> pd.DataFrame:
    capex = pd.read_csv(DATA_DIR / "fact_capex.csv", parse_dates=["Month"])
    return (
        capex.groupby(["Month", "Version", "Department"], as_index=False)
        .agg(
            CapexSpendTRY=("CapexSpendTRY", "sum"),
            DepreciationTRY=("DepreciationTRY", "sum"),
            RemainingNBVTRY=("RemainingNBVTRY", "sum"),
        )
        .sort_values(["Version", "Month", "Department"])
    )


def _dashboard_monthly(
    monthly: pd.DataFrame,
    cash: pd.DataFrame,
    working: pd.DataFrame,
    headcount_summary: pd.DataFrame,
    capex_summary: pd.DataFrame,
) -> pd.DataFrame:
    base = monthly[monthly["Year"] == 2026].copy()
    base = base.merge(
        cash[
            [
                "Month",
                "Version",
                "CashFromOperationsTRY",
                "CapitalExpenditureTRY",
                "EndingCashTRY",
            ]
        ],
        on=["Month", "Version"],
        how="left",
    )
    base = base.merge(
        working[
            [
                "Month",
                "Version",
                "DSO",
                "DIO",
                "DPO",
                "CashConversionCycleDays",
                "NetWorkingCapitalTRY",
            ]
        ],
        on=["Month", "Version"],
        how="left",
    )
    hc = headcount_summary.groupby(["Month", "Version"], as_index=False)[
        ["FTE", "Hires", "Exits", "PayrollCostTRY"]
    ].sum()
    base = base.merge(hc, on=["Month", "Version"], how="left")
    cp = capex_summary.groupby(["Month", "Version"], as_index=False)[
        ["CapexSpendTRY", "DepreciationTRY"]
    ].sum()
    base = base.merge(
        cp.rename(columns={"DepreciationTRY": "CapexScheduleDepreciationTRY"}),
        on=["Month", "Version"],
        how="left",
    )
    return base.sort_values(["Month", "Version"])


def _kpi_summary(
    annual: pd.DataFrame,
    cash: pd.DataFrame,
    working: pd.DataFrame,
    headcount: pd.DataFrame,
) -> pd.DataFrame:
    fy2025 = annual[(annual["Year"] == 2025) & (annual["Version"] == "Actual")].iloc[0]
    budget = annual[(annual["Year"] == 2026) & (annual["Version"] == "Budget")].iloc[0]
    forecast = annual[(annual["Year"] == 2026) & (annual["Version"] == "Forecast")].iloc[0]
    cash_lookup = cash.set_index(["Month", "Version"])["EndingCashTRY"]
    wc_lookup = working.set_index(["Month", "Version"])
    hc_lookup = (
        headcount.groupby(["Month", "Version"], as_index=False)["FTE"].sum()
        .set_index(["Month", "Version"])["FTE"]
    )
    rows = [
        ("Revenue", fy2025["RevenueTRY"], budget["RevenueTRY"], forecast["RevenueTRY"], "TRY", True),
        ("Gross Profit", fy2025["GrossProfitTRY"], budget["GrossProfitTRY"], forecast["GrossProfitTRY"], "TRY", True),
        ("Gross Margin", fy2025["GrossMarginPct"], budget["GrossMarginPct"], forecast["GrossMarginPct"], "Percent", True),
        ("EBITDA", fy2025["EBITDATRY"], budget["EBITDATRY"], forecast["EBITDATRY"], "TRY", True),
        ("EBITDA Margin", fy2025["EBITDAMarginPct"], budget["EBITDAMarginPct"], forecast["EBITDAMarginPct"], "Percent", True),
        ("Net Income", fy2025["NetIncomeTRY"], budget["NetIncomeTRY"], forecast["NetIncomeTRY"], "TRY", True),
        (
            "Ending Cash",
            cash_lookup[(pd.Timestamp("2025-12-01"), "Actual")],
            cash_lookup[(pd.Timestamp("2026-12-01"), "Budget")],
            cash_lookup[(pd.Timestamp("2026-12-01"), "Forecast")],
            "TRY",
            True,
        ),
        (
            "Cash Conversion Cycle",
            wc_lookup.loc[(pd.Timestamp("2025-12-01"), "Actual"), "CashConversionCycleDays"],
            wc_lookup.loc[(pd.Timestamp("2026-12-01"), "Budget"), "CashConversionCycleDays"],
            wc_lookup.loc[(pd.Timestamp("2026-12-01"), "Forecast"), "CashConversionCycleDays"],
            "Days",
            False,
        ),
        (
            "Headcount",
            hc_lookup[(pd.Timestamp("2025-12-01"), "Actual")],
            hc_lookup[(pd.Timestamp("2026-12-01"), "Budget")],
            hc_lookup[(pd.Timestamp("2026-12-01"), "Forecast")],
            "FTE",
            False,
        ),
    ]
    output = []
    for metric, prior, target, forecast_value, unit, higher_is_better in rows:
        variance = float(forecast_value) - float(target)
        variance_pct = variance / abs(float(target)) if target else np.nan
        favorable = variance >= 0 if higher_is_better else variance <= 0
        output.append(
            {
                "KPI": metric,
                "PriorYearActual": round(float(prior), 6),
                "BudgetTarget": round(float(target), 6),
                "RollingForecast": round(float(forecast_value), 6),
                "VarianceToBudget": round(variance, 6),
                "VariancePct": round(variance_pct, 6),
                "Unit": unit,
                "Status": "On / Above Plan" if favorable else "Action Required",
            }
        )
    return pd.DataFrame(output)


def _forecast_bridge() -> pd.DataFrame:
    budget = pd.read_csv(DATA_DIR / "fact_budget.csv")
    forecast = pd.read_csv(DATA_DIR / "fact_forecast.csv")
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    budget_pnl = aggregate_pnl(budget, accounts, ["Version"]).iloc[0]
    forecast_2026 = forecast[pd.to_datetime(forecast["Month"]).dt.year == 2026]
    forecast_pnl = aggregate_pnl(forecast_2026, accounts, ["Version"]).iloc[0]
    revenue_variance = float(forecast_pnl["RevenueTRY"] - budget_pnl["RevenueTRY"])
    gp_variance = float(forecast_pnl["GrossProfitTRY"] - budget_pnl["GrossProfitTRY"])
    ebitda_variance = float(forecast_pnl["EBITDATRY"] - budget_pnl["EBITDATRY"])
    budget_account = budget.groupby("AccountKey")["AmountTRY"].sum()
    forecast_account = forecast_2026.groupby("AccountKey")["AmountTRY"].sum()
    payroll_impact = -float(
        forecast_account.reindex(["A6000", "A6010"], fill_value=0).sum()
        - budget_account.reindex(["A6000", "A6010"], fill_value=0).sum()
    )
    marketing_impact = -float(
        forecast_account.get("A6100", 0) - budget_account.get("A6100", 0)
    )
    rows = [
        ("FY2026 Budget EBITDA", float(budget_pnl["EBITDATRY"]), 1),
        ("Volume Impact", revenue_variance * 0.58, 2),
        ("Price & Mix Impact", revenue_variance * 0.42, 3),
        ("Gross Margin / COGS Impact", gp_variance - revenue_variance, 4),
        ("Payroll Impact", payroll_impact, 5),
        ("Marketing Impact", marketing_impact, 6),
    ]
    explained = sum(value for _, value, _ in rows[1:])
    rows.append(("Other Operating Expense Impact", ebitda_variance - explained, 7))
    rows.append(("FY2026 Rolling Forecast EBITDA", float(forecast_pnl["EBITDATRY"]), 8))
    return pd.DataFrame(rows, columns=["BridgeItem", "ImpactTRY", "BridgeOrder"])


def _management_insights(
    annual: pd.DataFrame,
    kpis: pd.DataFrame,
    scenarios: pd.DataFrame,
    risk: pd.DataFrame,
) -> pd.DataFrame:
    budget = annual[(annual["Year"] == 2026) & (annual["Version"] == "Budget")].iloc[0]
    forecast = annual[(annual["Year"] == 2026) & (annual["Version"] == "Forecast")].iloc[0]
    base = scenarios[scenarios["Scenario"] == "Base"].iloc[0]
    stress = scenarios[scenarios["Scenario"] == "Stress"].iloc[0]
    risk_lookup = risk.set_index("RiskMetric")["Value"].to_dict()
    rows = [
        (
            1,
            "Revenue outlook",
            f"FY2026 rolling forecast revenue is {(forecast['RevenueTRY']/budget['RevenueTRY']-1):+.1%} versus budget.",
            "Protect high-growth digital and subscription channels while addressing retail softness.",
            "Commercial",
        ),
        (
            2,
            "Margin discipline",
            f"Forecast EBITDA margin is {forecast['EBITDAMarginPct']:.1%}, compared with {budget['EBITDAMarginPct']:.1%} in budget.",
            "Prioritize price/mix actions and supplier savings before discretionary cost cuts.",
            "Finance / Operations",
        ),
        (
            3,
            "Liquidity resilience",
            f"Base-case ending cash is TRY {base['EndingCashTRY']/1e6:.1f}m; the stress case retains TRY {stress['EndingCashTRY']/1e6:.1f}m.",
            "Maintain the capex gate and weekly cash forecast under downside conditions.",
            "Treasury",
        ),
        (
            4,
            "Working capital",
            f"Base-case cash conversion cycle is {base['CashConversionCycleDays']:.1f} days.",
            "Accelerate collections and reduce inventory days to close the gap to budget.",
            "Finance / Supply Chain",
        ),
        (
            5,
            "Forecast risk",
            f"Monte Carlo analysis estimates a {risk_lookup['Probability EBITDA Below Budget']:.1%} probability of EBITDA finishing below budget.",
            "Use trigger-based spend controls and scenario refreshes at each monthly close.",
            "FP&A",
        ),
        (
            6,
            "Planning governance",
            f"All cost-center submissions are approved as of {AS_OF_DATE}; rolling forecast accountability remains with budget owners.",
            "Track actions through a monthly business review and version-controlled assumptions log.",
            "Leadership Team",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=["InsightOrder", "Topic", "Evidence", "RecommendedAction", "Owner"],
    )


def build_reporting_tables() -> dict[str, pd.DataFrame]:
    monthly = _monthly_pnl()
    annual = _annual_pnl(monthly)
    variance = _variance_analysis(monthly)
    department = _performance_by_dimension(
        "Department", "department_performance.csv"
    )
    business_unit = _performance_by_dimension(
        "BusinessUnit", "business_unit_performance.csv"
    )
    headcount = _headcount_summary()
    capex = _capex_summary()
    cash = pd.read_csv(DATA_DIR / "fact_cash_flow.csv", parse_dates=["Month"])
    working = pd.read_csv(
        DATA_DIR / "fact_working_capital.csv", parse_dates=["Month"]
    )
    dashboard = _dashboard_monthly(
        monthly, cash, working, headcount, capex
    )
    kpis = _kpi_summary(annual, cash, working, headcount)
    bridge = _forecast_bridge()
    scenarios = pd.read_csv(DATA_DIR / "scenario_summary.csv")
    risk = pd.read_csv(DATA_DIR / "risk_summary.csv")
    insights = _management_insights(annual, kpis, scenarios, risk)
    cash_summary = (
        cash.groupby("Version", as_index=False)
        .agg(
            CashFromOperationsTRY=("CashFromOperationsTRY", "sum"),
            CapitalExpenditureTRY=("CapitalExpenditureTRY", "sum"),
            NetCashFlowTRY=("NetCashFlowTRY", "sum"),
            MinimumCashTRY=("EndingCashTRY", "min"),
            EndingCashTRY=("EndingCashTRY", "last"),
        )
    )

    tables = {
        "monthly_pnl": monthly,
        "annual_pnl": annual,
        "variance_analysis": variance,
        "department_performance": department,
        "business_unit_performance": business_unit,
        "headcount_summary": headcount,
        "capex_summary": capex,
        "monthly_kpi_dashboard": dashboard,
        "kpi_summary": kpis,
        "forecast_bridge": bridge,
        "cash_flow_summary": cash_summary,
        "management_insights": insights,
    }
    for name, frame in tables.items():
        frame.to_csv(
            DATA_DIR / f"{name}.csv",
            index=False,
            date_format="%Y-%m-%d",
        )
    return tables


if __name__ == "__main__":
    built = build_reporting_tables()
    print(f"{COMPANY_NAME} reporting tables")
    for table_name, frame in built.items():
        print(f"{table_name}: {len(frame):,} rows")
