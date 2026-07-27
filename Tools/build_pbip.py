from __future__ import annotations

import base64
import json
import shutil
import uuid
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Data"
POWERBI_DIR = PROJECT_ROOT / "PowerBI"
OUTPUT_ROOT = POWERBI_DIR / "Integrated_FPA_PBIP"
PROJECT_NAME = "Integrated_FPA_Planning_Analytics"
REPORT_NAME = f"{PROJECT_NAME}.Report"
MODEL_NAME = f"{PROJECT_NAME}.SemanticModel"
PBIP_PATH = OUTPUT_ROOT / f"{PROJECT_NAME}.pbip"
TEMPLATE_ROOT = (
    PROJECT_ROOT.parent
    / "outputs"
    / "crm_dashboard_suite"
    / "CRM_Sales_Analytics_PBIP"
)


def csv_m_expression(frame: pd.DataFrame, type_map: dict[str, str]) -> list[str]:
    export = frame.copy()
    for column in export.columns:
        if pd.api.types.is_datetime64_any_dtype(export[column]):
            export[column] = export[column].dt.strftime("%Y-%m-%d")
    csv_text = export.to_csv(index=False, lineterminator="\n")
    encoded = base64.b64encode(csv_text.encode("utf-8")).decode("ascii")
    type_pairs = ", ".join(
        f'{{"{column}", {power_query_type}}}'
        for column, power_query_type in type_map.items()
    )
    return [
        "let",
        f'    Binary = Binary.FromText("{encoded}", BinaryEncoding.Base64),',
        f'    Source = Csv.Document(Binary, [Delimiter=",", Columns={len(frame.columns)}, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f'    Typed = Table.TransformColumnTypes(Promoted, {{{type_pairs}}}, "en-US")',
        "in",
        "    Typed",
    ]


def column_metadata(frame: pd.DataFrame, type_map: dict[str, str]) -> list[dict]:
    columns = []
    for column in frame.columns:
        pq_type = type_map[column]
        if pq_type == "type date":
            metadata = {
                "name": column,
                "dataType": "dateTime",
                "sourceColumn": column,
                "formatString": "mmm yyyy" if column == "Month" else "yyyy-mm-dd",
            }
        elif pq_type == "Int64.Type":
            metadata = {
                "name": column,
                "dataType": "int64",
                "sourceColumn": column,
                "formatString": "#,0",
            }
        elif pq_type == "type number":
            metadata = {
                "name": column,
                "dataType": "double",
                "sourceColumn": column,
            }
        elif pq_type == "type logical":
            metadata = {
                "name": column,
                "dataType": "boolean",
                "sourceColumn": column,
            }
        else:
            metadata = {
                "name": column,
                "dataType": "string",
                "sourceColumn": column,
            }
        columns.append(metadata)
    return columns


def table_metadata(
    name: str,
    frame: pd.DataFrame,
    type_map: dict[str, str],
    measures: list[dict] | None = None,
) -> dict:
    table = {
        "name": name,
        "columns": column_metadata(frame, type_map),
        "partitions": [
            {
                "name": name,
                "mode": "import",
                "source": {
                    "type": "m",
                    "expression": csv_m_expression(frame, type_map),
                },
            }
        ],
    }
    if measures:
        table["measures"] = measures
    return table


def prepare_model_frames() -> dict[str, tuple[pd.DataFrame, dict[str, str]]]:
    monthly = pd.read_csv(DATA_DIR / "monthly_pnl.csv", parse_dates=["Month"])
    cash = pd.read_csv(DATA_DIR / "fact_cash_flow.csv", parse_dates=["Month"])
    working = pd.read_csv(
        DATA_DIR / "fact_working_capital.csv", parse_dates=["Month"]
    )
    headcount = pd.read_csv(DATA_DIR / "headcount_summary.csv", parse_dates=["Month"])
    department = pd.read_csv(
        DATA_DIR / "department_performance.csv", parse_dates=["Month"]
    )
    business_unit = pd.read_csv(
        DATA_DIR / "business_unit_performance.csv", parse_dates=["Month"]
    )
    scenarios = pd.read_csv(DATA_DIR / "scenario_summary.csv")
    variance = pd.read_csv(DATA_DIR / "variance_analysis.csv")
    risk = pd.read_csv(DATA_DIR / "risk_summary.csv")
    capex = pd.read_csv(DATA_DIR / "capex_summary.csv", parse_dates=["Month"])

    actual = monthly[monthly["Version"] == "Actual"].copy()
    actual = actual[actual["Month"] <= pd.Timestamp("2025-12-01")]
    forecast = monthly[monthly["Version"] == "Forecast"].copy()
    management = pd.concat([actual, forecast], ignore_index=True).sort_values("Month")
    budget = monthly[monthly["Version"] == "Budget"].set_index("Month")
    cash_forecast = cash[cash["Version"] == "Forecast"].set_index("Month")
    cash_actual = cash[cash["Version"] == "Actual"].set_index("Month")
    wc_forecast = working[working["Version"] == "Forecast"].set_index("Month")
    wc_actual = working[working["Version"] == "Actual"].set_index("Month")
    hc_forecast = (
        headcount[headcount["Version"] == "Forecast"]
        .groupby("Month")[["FTE"]]
        .sum()
    )
    hc_actual = (
        headcount[headcount["Version"] == "Actual"].groupby("Month")[["FTE"]].sum()
    )
    rows = []
    for _, row in management.iterrows():
        month = pd.Timestamp(row["Month"])
        is_forecast_view = month >= pd.Timestamp("2026-01-01")
        budget_row = budget.loc[month] if month in budget.index else None
        cash_row = (
            cash_forecast.loc[month]
            if is_forecast_view and month in cash_forecast.index
            else cash_actual.loc[month]
            if month in cash_actual.index
            else None
        )
        wc_row = (
            wc_forecast.loc[month]
            if is_forecast_view and month in wc_forecast.index
            else wc_actual.loc[month]
            if month in wc_actual.index
            else None
        )
        hc_value = (
            float(hc_forecast.loc[month, "FTE"])
            if is_forecast_view and month in hc_forecast.index
            else float(hc_actual.loc[month, "FTE"])
            if month in hc_actual.index
            else np.nan
        )
        budget_revenue = (
            float(budget_row["RevenueTRY"])
            if budget_row is not None
            else float(row["RevenueTRY"])
        )
        budget_ebitda = (
            float(budget_row["EBITDATRY"])
            if budget_row is not None
            else float(row["EBITDATRY"])
        )
        rows.append(
            {
                "Month": month,
                "Month Key": month.strftime("%Y-%m"),
                "Period": "Forecast" if is_forecast_view else "Actual",
                "Revenue": float(row["RevenueTRY"]),
                "Budget Revenue": budget_revenue,
                "Gross Profit": float(row["GrossProfitTRY"]),
                "Operating Expense": float(row["OperatingExpenseTRY"]),
                "EBITDA": float(row["EBITDATRY"]),
                "Budget EBITDA": budget_ebitda,
                "Depreciation": float(row["DepreciationTRY"]),
                "EBIT": float(row["EBITTRY"]),
                "Net Income": float(row["NetIncomeTRY"]),
                "Ending Cash": float(cash_row["EndingCashTRY"])
                if cash_row is not None
                else np.nan,
                "Headcount": int(round(hc_value)) if np.isfinite(hc_value) else 0,
                "CCC Days": float(wc_row["CashConversionCycleDays"])
                if wc_row is not None
                else np.nan,
                "Gross Margin Rate": float(row["GrossMarginPct"]),
                "EBITDA Margin": float(row["EBITDAMarginPct"]),
                "EBITDA Attainment": float(row["EBITDATRY"]) / budget_ebitda
                if budget_ebitda
                else 1.0,
                "Forecast Accuracy": float(row["ForecastAccuracyPct"])
                if pd.notna(row["ForecastAccuracyPct"])
                else 1.0,
            }
        )
    monthly_model = pd.DataFrame(rows)

    calendar = pd.DataFrame(
        {"Date": pd.date_range(monthly_model["Month"].min(), monthly_model["Month"].max(), freq="MS")}
    )
    calendar["Month"] = calendar["Date"].dt.strftime("%b %Y")
    calendar["Month Key"] = calendar["Date"].dt.strftime("%Y-%m")
    calendar["Year"] = calendar["Date"].dt.year
    calendar["Quarter"] = "Q" + calendar["Date"].dt.quarter.astype(str)

    department_forecast = department[
        (department["Version"] == "Forecast")
        & (department["Month"].dt.year == 2026)
    ].copy()
    department_budget = department[
        (department["Version"] == "Budget")
        & (department["Month"].dt.year == 2026)
    ][["Month", "Department", "RevenueTRY", "EBITDATRY"]].rename(
        columns={
            "RevenueTRY": "Budget Revenue",
            "EBITDATRY": "Budget EBITDA",
        }
    )
    department_model = department_forecast.merge(
        department_budget, on=["Month", "Department"], how="left"
    )
    hc_dept = headcount[
        (headcount["Version"] == "Forecast")
        & (headcount["Month"].dt.year == 2026)
    ][["Month", "Department", "FTE"]]
    department_model = department_model.merge(
        hc_dept, on=["Month", "Department"], how="left"
    )
    department_model = department_model.rename(
        columns={
            "RevenueTRY": "Revenue",
            "OperatingExpenseTRY": "Operating Expense",
            "EBITDATRY": "EBITDA",
            "EBITDAMarginPct": "EBITDA Margin",
            "FTE": "Headcount",
        }
    )[
        [
            "Month",
            "Department",
            "Revenue",
            "Budget Revenue",
            "Operating Expense",
            "EBITDA",
            "Budget EBITDA",
            "EBITDA Margin",
            "Headcount",
        ]
    ]

    bu_forecast = business_unit[
        (business_unit["Version"] == "Forecast")
        & (business_unit["Month"].dt.year == 2026)
    ].copy()
    business_unit_model = bu_forecast.rename(
        columns={
            "RevenueTRY": "Revenue",
            "GrossProfitTRY": "Gross Profit",
            "OperatingExpenseTRY": "Operating Expense",
            "GrossMarginPct": "Gross Margin",
        }
    )[
        [
            "Month",
            "BusinessUnit",
            "Revenue",
            "Gross Profit",
            "Operating Expense",
            "Gross Margin",
        ]
    ].rename(columns={"BusinessUnit": "Business Unit"})

    stages = pd.DataFrame(
        {
            "Stage": ["Revenue", "Gross Profit", "EBITDA", "EBIT", "Net Income"],
            "Stage Order": [1, 2, 3, 4, 5],
        }
    )
    scenario_model = scenarios.rename(
        columns={
            "ScenarioOrder": "Scenario Order",
            "RevenueTRY": "Revenue",
            "EBITDATRY": "EBITDA",
            "EndingCashTRY": "Ending Cash",
            "MinimumCashTRY": "Minimum Cash",
            "EBITDAMarginPct": "EBITDA Margin",
            "CashConversionCycleDays": "CCC Days",
        }
    )[
        [
            "Scenario",
            "Scenario Order",
            "Revenue",
            "EBITDA",
            "Ending Cash",
            "Minimum Cash",
            "EBITDA Margin",
            "CCC Days",
        ]
    ]
    variance_model = variance[
        variance["Comparison"] == "FY2026 Forecast vs Budget"
    ][
        [
            "Metric",
            "MetricOrder",
            "CurrentValueTRY",
            "ComparatorValueTRY",
            "VarianceTRY",
            "VariancePct",
            "Status",
        ]
    ].rename(
        columns={
            "MetricOrder": "Metric Order",
            "CurrentValueTRY": "Forecast Value",
            "ComparatorValueTRY": "Budget Value",
            "VarianceTRY": "Variance",
            "VariancePct": "Variance Rate",
        }
    )
    risk_model = risk.rename(columns={"RiskMetric": "Risk Metric"})
    capex_model = (
        capex[
            (capex["Version"] == "Forecast") & (capex["Month"].dt.year == 2026)
        ]
        .groupby("Department", as_index=False)[
            ["CapexSpendTRY", "DepreciationTRY", "RemainingNBVTRY"]
        ]
        .sum()
        .rename(
            columns={
                "CapexSpendTRY": "Capex Spend",
                "DepreciationTRY": "Depreciation",
                "RemainingNBVTRY": "Remaining NBV",
            }
        )
    )

    return {
        "dim_calendar": (
            calendar,
            {
                "Date": "type date",
                "Month": "type text",
                "Month Key": "type text",
                "Year": "Int64.Type",
                "Quarter": "type text",
            },
        ),
        "monthly_performance": (
            monthly_model,
            {
                "Month": "type date",
                "Month Key": "type text",
                "Period": "type text",
                "Revenue": "type number",
                "Budget Revenue": "type number",
                "Gross Profit": "type number",
                "Operating Expense": "type number",
                "EBITDA": "type number",
                "Budget EBITDA": "type number",
                "Depreciation": "type number",
                "EBIT": "type number",
                "Net Income": "type number",
                "Ending Cash": "type number",
                "Headcount": "Int64.Type",
                "CCC Days": "type number",
                "Gross Margin Rate": "type number",
                "EBITDA Margin": "type number",
                "EBITDA Attainment": "type number",
                "Forecast Accuracy": "type number",
            },
        ),
        "department_performance": (
            department_model,
            {
                "Month": "type date",
                "Department": "type text",
                "Revenue": "type number",
                "Budget Revenue": "type number",
                "Operating Expense": "type number",
                "EBITDA": "type number",
                "Budget EBITDA": "type number",
                "EBITDA Margin": "type number",
                "Headcount": "Int64.Type",
            },
        ),
        "business_unit_performance": (
            business_unit_model,
            {
                "Month": "type date",
                "Business Unit": "type text",
                "Revenue": "type number",
                "Gross Profit": "type number",
                "Operating Expense": "type number",
                "Gross Margin": "type number",
            },
        ),
        "P&L Stages": (
            stages,
            {"Stage": "type text", "Stage Order": "Int64.Type"},
        ),
        "scenario_summary": (
            scenario_model,
            {
                "Scenario": "type text",
                "Scenario Order": "Int64.Type",
                "Revenue": "type number",
                "EBITDA": "type number",
                "Ending Cash": "type number",
                "Minimum Cash": "type number",
                "EBITDA Margin": "type number",
                "CCC Days": "type number",
            },
        ),
        "variance_analysis": (
            variance_model,
            {
                "Metric": "type text",
                "Metric Order": "Int64.Type",
                "Forecast Value": "type number",
                "Budget Value": "type number",
                "Variance": "type number",
                "Variance Rate": "type number",
                "Status": "type text",
            },
        ),
        "risk_summary": (
            risk_model,
            {
                "Risk Metric": "type text",
                "Value": "type number",
                "Unit": "type text",
            },
        ),
        "capex_summary": (
            capex_model,
            {
                "Department": "type text",
                "Capex Spend": "type number",
                "Depreciation": "type number",
                "Remaining NBV": "type number",
            },
        ),
    }


def build_measures() -> dict[str, list[dict]]:
    monthly = [
        ("KPI Revenue", "SUM(monthly_performance[Revenue])", "₺#,0"),
        (
            "KPI Budget Revenue",
            "SUM(monthly_performance[Budget Revenue])",
            "₺#,0",
        ),
        ("KPI Gross Profit", "SUM(monthly_performance[Gross Profit])", "₺#,0"),
        (
            "KPI Operating Expense",
            "SUM(monthly_performance[Operating Expense])",
            "₺#,0",
        ),
        ("KPI EBITDA", "SUM(monthly_performance[EBITDA])", "₺#,0"),
        (
            "KPI Budget EBITDA",
            "SUM(monthly_performance[Budget EBITDA])",
            "₺#,0",
        ),
        (
            "KPI Depreciation",
            "SUM(monthly_performance[Depreciation])",
            "₺#,0",
        ),
        ("KPI EBIT", "SUM(monthly_performance[EBIT])", "₺#,0"),
        ("KPI Net Income", "SUM(monthly_performance[Net Income])", "₺#,0"),
        ("KPI Ending Cash", "MAX(monthly_performance[Ending Cash])", "₺#,0"),
        ("KPI Headcount", "MAX(monthly_performance[Headcount])", "#,0"),
        ("KPI CCC Days", "AVERAGE(monthly_performance[CCC Days])", "0.0"),
        (
            "KPI Gross Margin",
            "DIVIDE([KPI Gross Profit],[KPI Revenue],0)",
            "0.0%",
        ),
        (
            "KPI EBITDA Margin",
            "DIVIDE([KPI EBITDA],[KPI Revenue],0)",
            "0.0%",
        ),
        (
            "KPI EBITDA Attainment",
            "DIVIDE([KPI EBITDA],[KPI Budget EBITDA],0)",
            "0.0%",
        ),
        (
            "KPI Forecast Accuracy",
            "AVERAGE(monthly_performance[Forecast Accuracy])",
            "0.0%",
        ),
        (
            "KPI Revenue PY",
            "CALCULATE([KPI Revenue],DATEADD(dim_calendar[Date],-1,YEAR))",
            "₺#,0",
        ),
        (
            "KPI EBITDA PY",
            "CALCULATE([KPI EBITDA],DATEADD(dim_calendar[Date],-1,YEAR))",
            "₺#,0",
        ),
        (
            "KPI Revenue YoY %",
            "DIVIDE([KPI Revenue]-[KPI Revenue PY],[KPI Revenue PY],0)",
            "0.0%",
        ),
        (
            "KPI EBITDA YoY %",
            "DIVIDE([KPI EBITDA]-[KPI EBITDA PY],[KPI EBITDA PY],0)",
            "0.0%",
        ),
        (
            "KPI Revenue Variance",
            "[KPI Revenue]-[KPI Budget Revenue]",
            "₺#,0",
        ),
        (
            "KPI Revenue Variance %",
            "DIVIDE([KPI Revenue Variance],[KPI Budget Revenue],0)",
            "0.0%",
        ),
        ("KPI EBITDA Margin Target", "0.10", "0.0%"),
        ("KPI Cash Target", "200000000", "₺#,0"),
    ]
    department = [
        ("Dept Revenue", "SUM(department_performance[Revenue])", "₺#,0"),
        (
            "Dept Budget Revenue",
            "SUM(department_performance[Budget Revenue])",
            "₺#,0",
        ),
        (
            "Dept Operating Expense",
            "SUM(department_performance[Operating Expense])",
            "₺#,0",
        ),
        ("Dept EBITDA", "SUM(department_performance[EBITDA])", "₺#,0"),
        (
            "Dept EBITDA Margin",
            "DIVIDE([Dept EBITDA],[Dept Revenue],0)",
            "0.0%",
        ),
        ("Dept Headcount", "MAX(department_performance[Headcount])", "#,0"),
    ]
    business_unit = [
        ("BU Revenue", "SUM(business_unit_performance[Revenue])", "₺#,0"),
        (
            "BU Gross Profit",
            "SUM(business_unit_performance[Gross Profit])",
            "₺#,0",
        ),
        (
            "BU Operating Expense",
            "SUM(business_unit_performance[Operating Expense])",
            "₺#,0",
        ),
        (
            "BU Gross Margin",
            "DIVIDE([BU Gross Profit],[BU Revenue],0)",
            "0.0%",
        ),
    ]
    stages = [
        (
            "P&L Stage Value",
            'SWITCH(SELECTEDVALUE(\'P&L Stages\'[Stage]),"Revenue",[KPI Revenue],"Gross Profit",[KPI Gross Profit],"EBITDA",[KPI EBITDA],"EBIT",[KPI EBIT],"Net Income",[KPI Net Income],BLANK())',
            "₺#,0",
        )
    ]
    scenario = [
        ("Scenario Revenue", "SUM(scenario_summary[Revenue])", "₺#,0"),
        ("Scenario EBITDA", "SUM(scenario_summary[EBITDA])", "₺#,0"),
        (
            "Scenario Ending Cash",
            "SUM(scenario_summary[Ending Cash])",
            "₺#,0",
        ),
        (
            "Scenario Minimum Cash",
            "SUM(scenario_summary[Minimum Cash])",
            "₺#,0",
        ),
        (
            "Scenario EBITDA Margin",
            "DIVIDE([Scenario EBITDA],[Scenario Revenue],0)",
            "0.0%",
        ),
    ]

    def convert(items: list[tuple[str, str, str]]) -> list[dict]:
        return [
            {"name": name, "expression": expression, "formatString": fmt}
            for name, expression, fmt in items
        ]

    return {
        "monthly_performance": convert(monthly),
        "department_performance": convert(department),
        "business_unit_performance": convert(business_unit),
        "P&L Stages": convert(stages),
        "scenario_summary": convert(scenario),
    }


def build_semantic_model(model_dir: Path) -> None:
    template_model_path = (
        TEMPLATE_ROOT / "CRM_Sales_Analytics.SemanticModel" / "model.bim"
    )
    model = json.loads(template_model_path.read_text(encoding="utf-8"))
    frames = prepare_model_frames()
    measure_map = build_measures()
    model["model"]["tables"] = [
        table_metadata(name, frame, type_map, measure_map.get(name))
        for name, (frame, type_map) in frames.items()
    ]
    model["model"]["relationships"] = [
        {
            "name": "rel_monthly_calendar",
            "fromTable": "monthly_performance",
            "fromColumn": "Month",
            "toTable": "dim_calendar",
            "toColumn": "Date",
        },
        {
            "name": "rel_department_calendar",
            "fromTable": "department_performance",
            "fromColumn": "Month",
            "toTable": "dim_calendar",
            "toColumn": "Date",
        },
        {
            "name": "rel_business_unit_calendar",
            "fromTable": "business_unit_performance",
            "fromColumn": "Month",
            "toTable": "dim_calendar",
            "toColumn": "Date",
        },
    ]
    (model_dir / "model.bim").write_text(
        json.dumps(model, ensure_ascii=False, indent=2), encoding="utf-8"
    )


REPLACEMENTS = {
    "KPI Lead Qualification Rate": "KPI Gross Margin",
    "KPI Opportunity Conversion": "KPI EBITDA Margin",
    "KPI Target Attainment": "KPI EBITDA Attainment",
    "KPI Average Deal Size": "KPI Ending Cash",
    "KPI Revenue Variance %": "KPI Revenue Variance %",
    "KPI Revenue Variance": "KPI Revenue Variance",
    "KPI New Leads PY": "KPI Revenue PY",
    "KPI Won Revenue PY": "KPI EBITDA PY",
    "KPI Leads YoY %": "KPI Revenue YoY %",
    "KPI Revenue YoY %": "KPI EBITDA YoY %",
    "KPI Pipeline Target": "KPI Cash Target",
    "KPI Win Rate Target": "KPI EBITDA Margin Target",
    "KPI Sales Cycle Days": "KPI CCC Days",
    "KPI Qualified Leads": "KPI Gross Profit",
    "KPI Pipeline Value": "KPI Ending Cash",
    "KPI Revenue Target": "KPI Budget EBITDA",
    "KPI Won Revenue": "KPI EBITDA",
    "KPI New Customers": "KPI Headcount",
    "KPI Opportunities": "KPI Operating Expense",
    "KPI Won Deals": "KPI Net Income",
    "KPI Lead Target": "KPI Budget Revenue",
    "KPI New Leads": "KPI Revenue",
    "KPI Win Rate": "KPI EBITDA Margin",
    "KPI Churn Rate": "KPI Forecast Accuracy",
    "Rep Sales Cycle Days": "Dept Headcount",
    "Rep Revenue Target": "Dept Budget Revenue",
    "Rep Won Revenue": "Dept Revenue",
    "Rep Opportunities": "Dept Operating Expense",
    "Rep Won Deals": "Dept Headcount",
    "Rep Win Rate": "Dept EBITDA Margin",
    "Source Qualification Rate": "BU Gross Margin",
    "Source Acquisition Spend": "BU Operating Expense",
    "Source Qualified Leads": "BU Gross Profit",
    "Source New Leads": "BU Revenue",
    "Funnel Stage Value": "P&L Stage Value",
    "Lead Qualification Rate": "Gross Margin Rate",
    "Opportunity Conversion": "EBITDA Margin",
    "Average Deal Size": "Ending Cash",
    "Target Attainment": "EBITDA Attainment",
    "Sales Cycle Days": "CCC Days",
    "Qualified Leads": "Gross Profit",
    "Pipeline Value": "Ending Cash",
    "Revenue Target": "Budget EBITDA",
    "Won Revenue": "EBITDA",
    "New Customers": "Headcount",
    "Opportunities": "Operating Expense",
    "Won Deals": "Net Income",
    "Lead Target": "Budget Revenue",
    "New Leads": "Revenue",
    "Churn Rate": "Forecast Accuracy",
    "Win Rate": "EBITDA Margin",
    "Sales Rep": "Department",
    "Lead Source": "Business Unit",
    "Qualification Rate": "Gross Margin",
    "Acquisition Spend": "Operating Expense",
    "crm_rep_performance": "department_performance",
    "crm_lead_sources": "business_unit_performance",
    "crm_monthly": "monthly_performance",
    "Funnel Stages": "P&L Stages",
    "Calendar": "dim_calendar",
    "CRM SALES ANALYTICS": "INTEGRATED FP&A ANALYTICS",
    "CRM Sales Analytics": "Integrated FP&A Analytics",
    "Lead Generation": "Revenue & Margin",
    "Sales Funnel": "P&L Waterfall",
    "Revenue Performance": "Budget vs Actual",
    "Pipeline Analysis": "Rolling Forecast",
    "Sales Rep Performance": "Department Performance",
    "Lead Source Analysis": "Business Unit Analysis",
    "Customer & Segments": "Cash & Working Capital",
    "Target vs Actual": "Operating Expense",
    "Three-Year Trends": "Long-Range Trends",
    "LEAD GENERATION": "REVENUE & MARGIN",
    "SALES FUNNEL": "P&L WATERFALL",
    "PIPELINE ANALYSIS": "ROLLING FORECAST",
    "SALES REP PERFORMANCE": "DEPARTMENT PERFORMANCE",
    "LEAD SOURCE ANALYSIS": "BUSINESS UNIT ANALYSIS",
    "CUSTOMER & SEGMENTS": "CASH & WORKING CAPITAL",
    "TARGET VS ACTUAL": "OPERATING EXPENSE",
    "THREE-YEAR TRENDS": "LONG-RANGE TRENDS",
    "Leads Actual vs Target": "Revenue vs Budget",
    "Leads by Source": "Revenue by Business Unit",
    "Lead Mix by Source": "Revenue Mix by Business Unit",
    "New and Qualified Leads by Source": "Revenue and Gross Profit by Business Unit",
    "New and Fulfilled Demand by Source": "Revenue and Gross Profit by Business Unit",
    "Pipeline and Target Trend": "Ending Cash & Target Trend",
    "Revenue Actual vs Target": "EBITDA vs Budget",
    "Revenue — Actual vs Target": "EBITDA vs Budget",
    "Rep Revenue vs Target": "Department Revenue vs Budget",
    "Selected Month Funnel": "Selected Month P&L Flow",
    "Conversion Rates": "Gross & EBITDA Margins",
    "36-Month Commercial Trend": "54-Month Financial Trend",
    "36-Month Conversion Trend": "54-Month Margin Trend",
    "Three-Year Revenue Trend": "Historical & Forecast Revenue Trend",
    "Monthly Revenue Variance": "Monthly Revenue Variance",
    "New Customer Trend": "Headcount Trend",
    "CUSTOMER REVENUE": "ENDING CASH",
    "NEW CUSTOMERS": "HEADCOUNT",
    "CHURN RATE": "FORECAST ACCURACY",
    "AVG DEAL SIZE": "ENDING CASH",
    "TEAM SERVICE LEVEL": "DEPARTMENT EBITDA MARGIN",
    "TEAM WIN RATE": "DEPARTMENT EBITDA MARGIN",
    "TEAM TARGET": "DEPARTMENT BUDGET",
    "TEAM REVENUE": "DEPARTMENT REVENUE",
    "INVENTORY TARGET": "CASH TARGET",
    "PIPELINE TARGET": "CASH TARGET",
    "REVENUE TARGET": "BUDGET EBITDA",
    "ACTUAL REVENUE": "FORECAST EBITDA",
    "QUALIFICATION RATE": "GROSS MARGIN",
    "TOTAL LEADS": "REVENUE",
    "WON DEALS": "NET INCOME",
    "OPPORTUNITIES": "OPERATING EXPENSE",
    "QUALIFIED": "GROSS PROFIT",
    "ATTAINMENT": "EBITDA ATTAINMENT",
    "YOY GROWTH": "REVENUE YOY",
    "TARGET": "BUDGET",
    "NEW LEADS": "REVENUE",
    "QUALIFIED LEADS": "GROSS PROFIT",
    "WON REVENUE": "EBITDA",
    "LEAD TARGET": "BUDGET REVENUE",
    "PIPELINE": "ENDING CASH",
    "WIN RATE": "EBITDA MARGIN",
    "SALES CYCLE": "CCC DAYS",
    "SALES REP": "DEPARTMENT",
    "LEAD SOURCE": "BUSINESS UNIT",
}


PAGE_NAMES = [
    "1. Executive Overview",
    "2. Revenue & Margin",
    "3. P&L Waterfall",
    "4. Budget vs Actual",
    "5. Rolling Forecast",
    "6. Department Performance",
    "7. Business Unit Analysis",
    "8. Cash & Working Capital",
    "9. Operating Expense",
    "10. Long-Range Trends",
]


def replace_report_text(report_dir: Path) -> None:
    for path in report_dir.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        for old, new in sorted(
            REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True
        ):
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")

    pages_meta = json.loads(
        (report_dir / "definition" / "pages" / "pages.json").read_text(
            encoding="utf-8"
        )
    )
    for display_name, page_name in zip(
        PAGE_NAMES, pages_meta["pageOrder"], strict=True
    ):
        page_path = report_dir / "definition" / "pages" / page_name / "page.json"
        page = json.loads(page_path.read_text(encoding="utf-8"))
        page["displayName"] = display_name
        page_path.write_text(
            json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def clone_scenario_page(report_dir: Path) -> None:
    pages_root = report_dir / "definition" / "pages"
    meta_path = pages_root / "pages.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    source_page_name = meta["pageOrder"][6]
    new_page_name = "ReportSection" + uuid.uuid5(
        uuid.NAMESPACE_URL, "integrated-fpa-scenario-page"
    ).hex[:20]
    source_dir = pages_root / source_page_name
    target_dir = pages_root / new_page_name
    shutil.copytree(source_dir, target_dir)
    page_path = target_dir / "page.json"
    page = json.loads(page_path.read_text(encoding="utf-8"))
    page["name"] = new_page_name
    page["displayName"] = "11. Scenario Planning & Risk"
    page_path.write_text(
        json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    scenario_replacements = {
        "business_unit_performance": "scenario_summary",
        "BU Operating Expense": "Scenario Ending Cash",
        "BU Gross Profit": "Scenario EBITDA",
        "BU Gross Margin": "Scenario EBITDA Margin",
        "BU Revenue": "Scenario Revenue",
        "Business Unit": "Scenario",
        "BUSINESS UNIT ANALYSIS": "SCENARIO PLANNING & RISK",
        "Business Unit Analysis": "Scenario Planning & Risk",
        "Revenue by Scenario": "Revenue by Scenario",
        "Revenue Mix by Scenario": "Revenue Mix by Scenario",
        "Revenue and Gross Profit by Scenario": "Revenue and EBITDA by Scenario",
        "Operating Expense": "Ending Cash",
        "Gross Profit": "EBITDA",
        "Gross Margin": "EBITDA Margin",
    }
    for path in target_dir.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        for old, new in sorted(
            scenario_replacements.items(), key=lambda item: len(item[0]), reverse=True
        ):
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
    meta["pageOrder"].append(new_page_name)
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def update_theme_and_metadata(report_dir: Path, model_dir: Path) -> None:
    old_theme = (
        report_dir
        / "StaticResources"
        / "RegisteredResources"
        / "CRMModernDark-7f3c2a91.json"
    )
    new_theme_name = "IntegratedFPADark-7f3c2a91.json"
    new_theme = old_theme.with_name(new_theme_name)
    theme = json.loads(old_theme.read_text(encoding="utf-8"))
    theme["name"] = new_theme_name
    theme["dataColors"] = [
        "#39C6F4",
        "#2F6BFF",
        "#0F9D7A",
        "#F6B73C",
        "#D9534F",
        "#8B5CF6",
    ]
    new_theme.write_text(
        json.dumps(theme, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    old_theme.unlink()

    report_json_path = report_dir / "definition" / "report.json"
    report_json = json.loads(report_json_path.read_text(encoding="utf-8"))
    report_json["themeCollection"]["customTheme"]["name"] = new_theme_name
    report_json["resourcePackages"][0]["items"][0]["name"] = new_theme_name
    report_json["resourcePackages"][0]["items"][0]["path"] = new_theme_name
    report_json_path.write_text(
        json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for platform_path, display_name, logical_id in (
        (
            report_dir / ".platform",
            "Integrated FP&A Planning Analytics",
            "integrated-fpa-report",
        ),
        (
            model_dir / ".platform",
            "Integrated FP&A Planning Analytics",
            "integrated-fpa-model",
        ),
    ):
        platform = json.loads(platform_path.read_text(encoding="utf-8"))
        platform["metadata"]["displayName"] = display_name
        platform["config"]["logicalId"] = str(
            uuid.uuid5(uuid.NAMESPACE_URL, logical_id)
        )
        platform_path.write_text(
            json.dumps(platform, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def write_measure_catalog() -> None:
    lines = [
        "// Integrated FP&A Planning Analytics - reusable DAX measure catalog",
        "// Generated from the semantic model definition.",
        "",
    ]
    for table, measures in build_measures().items():
        lines.append(f"// [{table}]")
        for measure in measures:
            lines.append(f"{measure['name']} = {measure['expression']}")
        lines.append("")
    POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    (POWERBI_DIR / "Integrated_FPA_Measures.dax").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def validate_pbip(report_dir: Path, model_dir: Path) -> dict:
    errors: list[str] = []
    json_files = list(report_dir.rglob("*.json")) + [
        report_dir / ".platform",
        report_dir / "definition.pbir",
        model_dir / ".platform",
        model_dir / "definition.pbism",
        model_dir / "model.bim",
        PBIP_PATH,
    ]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(
                f"Invalid JSON: {path.relative_to(OUTPUT_ROOT)}: {exc}"
            )

    pages_root = report_dir / "definition" / "pages"
    page_files = list(pages_root.glob("*/page.json"))
    if len(page_files) != 11:
        errors.append(f"Expected 11 pages; found {len(page_files)}")
    for page_file in page_files:
        page = json.loads(page_file.read_text(encoding="utf-8"))
        if page.get("width") != 1280 or page.get("height") != 720:
            errors.append(f"Non-HD page canvas: {page.get('displayName')}")
        visual_count = len(list(page_file.parent.glob("visuals/*/visual.json")))
        if visual_count < 4:
            errors.append(
                f"Too few visuals on {page.get('displayName')}: {visual_count}"
            )

    model = json.loads((model_dir / "model.bim").read_text(encoding="utf-8"))
    table_names = {table["name"] for table in model["model"]["tables"]}
    report_text = "\n".join(
        path.read_text(encoding="utf-8") for path in report_dir.rglob("*.json")
    )
    model_text = (model_dir / "model.bim").read_text(encoding="utf-8")
    for token in [
        "crm_",
        "CRM SALES",
        "Lead Generation",
        "Sales Funnel",
        "Leads ",
        "Lead ",
        "LEAD",
        "Won Deals",
        "WON DEALS",
        "Pipeline",
        "PIPELINE",
    ]:
        if token in report_text or token in model_text:
            errors.append(f"Legacy CRM token remains: {token}")

    entity_values = set()

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "Entity" and isinstance(item, str):
                    entity_values.add(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for path in report_dir.rglob("visual.json"):
        walk(json.loads(path.read_text(encoding="utf-8")))
    unknown_entities = sorted(entity_values - table_names)
    if unknown_entities:
        errors.append(f"Unknown visual entities: {unknown_entities}")

    report = {
        "project": PROJECT_NAME,
        "pages": len(page_files),
        "visuals": len(list(report_dir.rglob("visual.json"))),
        "tables": sorted(table_names),
        "relationships": len(model["model"].get("relationships", [])),
        "valid": not errors,
        "errors": errors,
    }
    (OUTPUT_ROOT / "pbip_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def build_pbip() -> Path:
    if not TEMPLATE_ROOT.exists():
        raise FileNotFoundError(f"PBIP template not found: {TEMPLATE_ROOT}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    report_dir = OUTPUT_ROOT / REPORT_NAME
    model_dir = OUTPUT_ROOT / MODEL_NAME
    shutil.copytree(
        TEMPLATE_ROOT / "CRM_Sales_Analytics.Report",
        report_dir,
    )
    shutil.copytree(
        TEMPLATE_ROOT / "CRM_Sales_Analytics.SemanticModel",
        model_dir,
    )
    definition_pbir = json.loads(
        (report_dir / "definition.pbir").read_text(encoding="utf-8")
    )
    definition_pbir["datasetReference"]["byPath"]["path"] = f"../{MODEL_NAME}"
    (report_dir / "definition.pbir").write_text(
        json.dumps(definition_pbir, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pbip = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": REPORT_NAME}}],
        "settings": {"enableAutoRecovery": True},
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    PBIP_PATH.write_text(
        json.dumps(pbip, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    build_semantic_model(model_dir)
    replace_report_text(report_dir)
    clone_scenario_page(report_dir)
    update_theme_and_metadata(report_dir, model_dir)
    write_measure_catalog()

    readme = """Integrated FP&A Budgeting, Forecasting & Scenario Planning - Power BI Project

Open Integrated_FPA_Planning_Analytics.pbip with a current version of Power BI Desktop.
The semantic model embeds the synthetic portfolio data in Base64 Power Query partitions;
no local CSV path remapping is required.

Pages:
1. Executive Overview
2. Revenue & Margin
3. P&L Waterfall
4. Budget vs Actual
5. Rolling Forecast
6. Department Performance
7. Business Unit Analysis
8. Cash & Working Capital
9. Operating Expense
10. Long-Range Trends
11. Scenario Planning & Risk

Data notice: Asteria Consumer Group is a synthetic portfolio entity. No real company,
employee, customer, supplier or bank records are included.
"""
    (OUTPUT_ROOT / "README.txt").write_text(readme, encoding="utf-8")
    report = validate_pbip(report_dir, model_dir)
    if not report["valid"]:
        raise RuntimeError(json.dumps(report, ensure_ascii=False, indent=2))
    archive_path = POWERBI_DIR / "Integrated_FPA_Planning_PBIP.zip"
    if archive_path.exists():
        archive_path.unlink()
    shutil.make_archive(
        str(archive_path.with_suffix("")),
        "zip",
        root_dir=OUTPUT_ROOT,
    )
    return PBIP_PATH


if __name__ == "__main__":
    print(build_pbip())
