from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import (
    ACCOUNT_ROWS,
    ACTUAL_END,
    ACTUAL_START,
    AS_OF_DATE,
    BUDGET_END,
    BUDGET_START,
    COMPANY_NAME,
    COST_CENTER_ROWS,
    DATA_DIR,
    RANDOM_SEED,
    REVENUE_ACCOUNT_BY_BU,
    ROLLING_FORECAST_END,
)


@dataclass(frozen=True)
class CostCenterProfile:
    cost_center_id: str
    cost_center_name: str
    department: str
    business_unit: str
    region: str
    base_monthly_revenue: float
    annual_growth: float
    product_cost_ratio: float
    fee_ratio: float
    fulfillment_ratio: float
    opening_fte: int
    average_salary: float


def _profiles() -> list[CostCenterProfile]:
    return [CostCenterProfile(*row) for row in COST_CENTER_ROWS]


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def build_calendar() -> pd.DataFrame:
    months = pd.date_range(ACTUAL_START, ROLLING_FORECAST_END, freq="MS")
    frame = pd.DataFrame({"Date": months})
    frame["MonthKey"] = frame["Date"].dt.strftime("%Y-%m")
    frame["MonthLabel"] = frame["Date"].dt.strftime("%b %Y")
    frame["MonthName"] = frame["Date"].dt.strftime("%B")
    frame["MonthNo"] = frame["Date"].dt.month
    frame["Quarter"] = "Q" + frame["Date"].dt.quarter.astype(str)
    frame["Year"] = frame["Date"].dt.year
    frame["FiscalYear"] = "FY" + frame["Year"].astype(str)
    frame["MonthIndex"] = np.arange(1, len(frame) + 1)
    frame["IsActual"] = frame["Date"] <= pd.Timestamp(ACTUAL_END)
    frame["IsBudgetYear"] = frame["Year"] == 2026
    frame["IsRollingForecast"] = (
        (frame["Date"] > pd.Timestamp(ACTUAL_END))
        & (frame["Date"] <= pd.Timestamp(ROLLING_FORECAST_END))
    )
    return frame


def build_accounts() -> pd.DataFrame:
    return pd.DataFrame(
        ACCOUNT_ROWS,
        columns=[
            "AccountKey",
            "AccountCode",
            "AccountName",
            "AccountGroup",
            "Statement",
            "NaturalSign",
            "PrimaryDriver",
        ],
    )


def build_cost_centers() -> pd.DataFrame:
    frame = pd.DataFrame(
        COST_CENTER_ROWS,
        columns=[
            "CostCenterID",
            "CostCenterName",
            "Department",
            "BusinessUnit",
            "Region",
            "BaseMonthlyRevenueTRY",
            "AnnualGrowthRate",
            "ProductCostRatio",
            "FeeRatio",
            "FulfillmentRatio",
            "OpeningFTE",
            "AverageMonthlySalaryTRY",
        ],
    )
    frame["BudgetOwner"] = frame["Department"].map(
        {
            "Sales": "Commercial Director",
            "Customer Success": "Customer Experience Director",
            "Marketing": "Marketing Director",
            "Operations": "Operations Director",
            "Technology": "CTO",
            "Finance & Corporate": "CFO",
        }
    )
    return frame


def build_scenarios() -> pd.DataFrame:
    rows = [
        {
            "Scenario": "Base",
            "ScenarioOrder": 1,
            "Description": "Most likely operating plan using the Q2 2026 rolling forecast.",
        },
        {
            "Scenario": "Upside",
            "ScenarioOrder": 2,
            "Description": "Stronger demand, favorable mix and tighter working-capital execution.",
        },
        {
            "Scenario": "Downside",
            "ScenarioOrder": 3,
            "Description": "Softer demand and modest gross-margin pressure with controlled spend.",
        },
        {
            "Scenario": "Stress",
            "ScenarioOrder": 4,
            "Description": "Severe demand contraction, input-cost pressure and slower collections.",
        },
    ]
    return pd.DataFrame(rows)


def _seasonality(profile: CostCenterProfile, month: int) -> float:
    if profile.business_unit == "Digital Commerce":
        factors = {
            1: 0.88,
            2: 0.90,
            3: 0.96,
            4: 0.98,
            5: 1.02,
            6: 1.04,
            7: 0.99,
            8: 0.95,
            9: 1.02,
            10: 1.08,
            11: 1.25,
            12: 1.36,
        }
    elif profile.business_unit == "Retail Stores":
        factors = {
            1: 0.84,
            2: 0.86,
            3: 0.96,
            4: 1.00,
            5: 1.04,
            6: 1.09,
            7: 1.08,
            8: 0.94,
            9: 1.03,
            10: 1.05,
            11: 1.08,
            12: 1.29,
        }
    elif profile.business_unit == "Wholesale":
        factors = {
            1: 0.91,
            2: 0.96,
            3: 1.06,
            4: 1.08,
            5: 1.01,
            6: 0.94,
            7: 0.84,
            8: 0.91,
            9: 1.18,
            10: 1.16,
            11: 1.02,
            12: 0.93,
        }
    elif profile.business_unit == "Subscription Services":
        factors = {
            1: 0.95,
            2: 0.96,
            3: 0.98,
            4: 0.99,
            5: 1.00,
            6: 1.01,
            7: 1.02,
            8: 1.03,
            9: 1.04,
            10: 1.05,
            11: 1.06,
            12: 1.07,
        }
    else:
        return 1.0
    return factors[month]


def build_headcount(
    rng: np.random.Generator,
    calendar: pd.DataFrame,
    cost_centers: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict] = []
    actual_months = calendar.loc[calendar["IsActual"], "Date"].tolist()
    budget_months = pd.date_range(BUDGET_START, BUDGET_END, freq="MS")
    forecast_months = pd.date_range(BUDGET_START, ROLLING_FORECAST_END, freq="MS")

    for _, cc in cost_centers.iterrows():
        opening = int(cc["OpeningFTE"])
        actual_fte = opening
        salary = float(cc["AverageMonthlySalaryTRY"])
        for idx, month in enumerate(actual_months):
            if idx > 0:
                hire_probability = 0.12 if cc["Department"] in ("Sales", "Technology") else 0.08
                hires = int(rng.random() < hire_probability)
                exits = int(rng.random() < 0.055)
                actual_fte = max(2, actual_fte + hires - exits)
            annual_step = 1.0 + 0.24 * max(month.year - 2023, 0)
            merit = 1.06 if month.month == 4 else 1.0
            if month.month == 4:
                salary *= merit
            monthly_salary = salary * annual_step / max(1.0 + 0.24 * max(month.year - 2023, 0), 1)
            overtime = 1.025 if cc["Department"] in ("Sales", "Operations") and month.month in (11, 12) else 1.0
            payroll = actual_fte * monthly_salary * overtime * float(rng.normal(1.0, 0.012))
            rows.append(
                {
                    "Month": month,
                    "CostCenterID": cc["CostCenterID"],
                    "Department": cc["Department"],
                    "Version": "Actual",
                    "FTE": actual_fte,
                    "Hires": hires if idx > 0 else 0,
                    "Exits": exits if idx > 0 else 0,
                    "AverageSalaryTRY": round(monthly_salary, 2),
                    "PayrollCostTRY": round(payroll, 2),
                    "BenefitsCostTRY": round(payroll * 0.185, 2),
                }
            )

        dec_2025 = [
            row
            for row in rows
            if row["CostCenterID"] == cc["CostCenterID"]
            and row["Version"] == "Actual"
            and pd.Timestamp(row["Month"]) == pd.Timestamp("2025-12-01")
        ][0]
        budget_fte = int(dec_2025["FTE"])
        budget_salary = float(dec_2025["AverageSalaryTRY"]) * 1.16
        growth_hires = {
            "Sales": 2,
            "Customer Success": 2,
            "Marketing": 1,
            "Operations": 2,
            "Technology": 3,
            "Finance & Corporate": 1,
        }[cc["Department"]]
        hire_months = np.linspace(2, 10, growth_hires, dtype=int).tolist()
        for month in budget_months:
            hires = hire_months.count(month.month)
            exits = 1 if month.month == 9 and budget_fte >= 20 else 0
            budget_fte += hires - exits
            rows.append(
                {
                    "Month": month,
                    "CostCenterID": cc["CostCenterID"],
                    "Department": cc["Department"],
                    "Version": "Budget",
                    "FTE": budget_fte,
                    "Hires": hires,
                    "Exits": exits,
                    "AverageSalaryTRY": round(budget_salary, 2),
                    "PayrollCostTRY": round(budget_fte * budget_salary, 2),
                    "BenefitsCostTRY": round(budget_fte * budget_salary * 0.185, 2),
                }
            )

        june_actual = [
            row
            for row in rows
            if row["CostCenterID"] == cc["CostCenterID"]
            and row["Version"] == "Actual"
            and pd.Timestamp(row["Month"]) == pd.Timestamp(ACTUAL_END)
        ][0]
        forecast_fte = int(june_actual["FTE"])
        forecast_salary = float(june_actual["AverageSalaryTRY"])
        for month in forecast_months:
            if month <= pd.Timestamp(ACTUAL_END):
                actual = [
                    row
                    for row in rows
                    if row["CostCenterID"] == cc["CostCenterID"]
                    and row["Version"] == "Actual"
                    and pd.Timestamp(row["Month"]) == month
                ][0]
                rows.append({**actual, "Version": "Forecast"})
                continue
            hires = 0
            if (
                month.month in (8, 11, 2)
                and cc["Department"] in ("Sales", "Technology", "Operations")
            ):
                hires = 1
            exits = 1 if month.month == 10 and forecast_fte > 15 else 0
            forecast_fte += hires - exits
            if month.month == 4:
                forecast_salary *= 1.15
            payroll = forecast_fte * forecast_salary
            rows.append(
                {
                    "Month": month,
                    "CostCenterID": cc["CostCenterID"],
                    "Department": cc["Department"],
                    "Version": "Forecast",
                    "FTE": forecast_fte,
                    "Hires": hires,
                    "Exits": exits,
                    "AverageSalaryTRY": round(forecast_salary, 2),
                    "PayrollCostTRY": round(payroll, 2),
                    "BenefitsCostTRY": round(payroll * 0.185, 2),
                }
            )
    return pd.DataFrame(rows)


def build_capex(
    calendar: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    projects = pd.DataFrame(
        [
            ("CPX-001", "Retail POS Modernization", "Technology", "CC-701", "2023-02-01", "2023-06-01", 8_400_000, 8_150_000, 48, "Completed"),
            ("CPX-002", "Flagship Store Refurbishment", "Sales", "CC-201", "2023-05-01", "2023-10-01", 6_200_000, 6_450_000, 60, "Completed"),
            ("CPX-003", "Cloud Data Platform", "Technology", "CC-701", "2024-01-01", "2024-07-01", 12_800_000, 12_300_000, 48, "Completed"),
            ("CPX-004", "Fulfillment Automation", "Operations", "CC-601", "2024-04-01", "2024-11-01", 15_500_000, 15_900_000, 72, "Completed"),
            ("CPX-005", "Customer Experience Platform", "Customer Success", "CC-401", "2025-01-01", "2025-06-01", 9_600_000, 9_350_000, 48, "Completed"),
            ("CPX-006", "Regional Store Upgrade", "Sales", "CC-202", "2025-03-01", "2025-09-01", 7_800_000, 8_050_000, 60, "Completed"),
            ("CPX-007", "Finance Planning System", "Finance & Corporate", "CC-801", "2025-07-01", "2026-03-01", 10_500_000, 10_200_000, 60, "Completed"),
            ("CPX-008", "AI Forecasting Workbench", "Technology", "CC-701", "2026-02-01", "2026-10-01", 13_500_000, 12_900_000, 48, "In Progress"),
            ("CPX-009", "Warehouse Capacity Expansion", "Operations", "CC-601", "2026-04-01", "2027-01-01", 18_000_000, 17_600_000, 72, "Approved"),
            ("CPX-010", "Subscription Mobile Experience", "Customer Success", "CC-401", "2026-07-01", "2027-03-01", 11_200_000, 10_850_000, 48, "Approved"),
        ],
        columns=[
            "ProjectID",
            "ProjectName",
            "Department",
            "CostCenterID",
            "StartMonth",
            "InServiceMonth",
            "BudgetTRY",
            "ForecastCostTRY",
            "UsefulLifeMonths",
            "Status",
        ],
    )
    projects["StartMonth"] = pd.to_datetime(projects["StartMonth"])
    projects["InServiceMonth"] = pd.to_datetime(projects["InServiceMonth"])
    projects["BudgetVarianceTRY"] = projects["ForecastCostTRY"] - projects["BudgetTRY"]
    projects["BudgetVariancePct"] = projects["BudgetVarianceTRY"] / projects["BudgetTRY"]

    rows: list[dict] = []
    actual_end = pd.Timestamp(ACTUAL_END)
    for _, project in projects.iterrows():
        for version in ("Actual", "Budget", "Forecast"):
            if version == "Actual":
                cost = (
                    float(project["ForecastCostTRY"])
                    if project["InServiceMonth"] <= actual_end
                    else 0.0
                )
            elif version == "Budget":
                cost = float(project["BudgetTRY"])
            else:
                cost = float(project["ForecastCostTRY"])
            for month in calendar["Date"]:
                if version == "Actual" and month > actual_end:
                    continue
                spend = 0.0
                if project["StartMonth"] <= month <= project["InServiceMonth"]:
                    duration = (
                        (project["InServiceMonth"].year - project["StartMonth"].year) * 12
                        + project["InServiceMonth"].month
                        - project["StartMonth"].month
                        + 1
                    )
                    spend = cost / duration if cost else 0.0
                months_in_service = (
                    (month.year - project["InServiceMonth"].year) * 12
                    + month.month
                    - project["InServiceMonth"].month
                )
                depreciation = (
                    cost / int(project["UsefulLifeMonths"])
                    if 0 <= months_in_service < int(project["UsefulLifeMonths"])
                    else 0.0
                )
                accumulated = min(
                    max(months_in_service + 1, 0) * depreciation,
                    cost,
                )
                rows.append(
                    {
                        "Month": month,
                        "ProjectID": project["ProjectID"],
                        "CostCenterID": project["CostCenterID"],
                        "Department": project["Department"],
                        "Version": version,
                        "CapexSpendTRY": round(spend, 2),
                        "DepreciationTRY": round(depreciation, 2),
                        "RemainingNBVTRY": round(max(cost - accumulated, 0), 2),
                    }
                )
    return projects, pd.DataFrame(rows)


def _fixed_opex(
    profile: CostCenterProfile,
    month: pd.Timestamp,
    revenue: float,
    rng: np.random.Generator,
) -> dict[str, float]:
    inflation = (1.17 ** max(month.year - 2023, 0)) * (1 + 0.010 * (month.month - 1))
    department = profile.department
    marketing = revenue * (0.050 if profile.business_unit == "Digital Commerce" else 0.020)
    logistics = revenue * (0.018 if profile.business_unit in ("Digital Commerce", "Retail Stores") else 0.010)
    technology = 90_000 * profile.opening_fte / 10
    facilities = 115_000 * profile.opening_fte / 10 if profile.business_unit == "Retail Stores" else 45_000 * profile.opening_fte / 10
    professional = 24_000 * profile.opening_fte / 10
    travel = 15_000 * profile.opening_fte / 10

    if department == "Marketing":
        marketing = 2_850_000 * inflation
        logistics = 0
        technology = 180_000
        facilities = 65_000
        professional = 240_000
        travel = 110_000
    elif department == "Operations":
        marketing = 0
        logistics = 3_150_000 * inflation
        technology = 310_000
        facilities = 850_000
        professional = 185_000
        travel = 85_000
    elif department == "Technology":
        marketing = 0
        logistics = 0
        technology = 2_750_000
        facilities = 190_000
        professional = 720_000
        travel = 145_000
    elif department == "Finance & Corporate":
        marketing = 0
        logistics = 0
        technology = 480_000
        facilities = 980_000
        professional = 1_050_000
        travel = 240_000
    elif department == "Customer Success":
        marketing += 180_000 * inflation
        technology += 420_000

    def shock(scale: float = 0.02) -> float:
        return float(rng.normal(1.0, scale))

    return {
        "A6100": max(marketing * shock(), 0),
        "A6200": max(logistics * shock(), 0),
        "A6300": max(technology * inflation * shock(), 0),
        "A6400": max(facilities * inflation * shock(0.01), 0),
        "A6500": max(professional * inflation * shock(0.05), 0),
        "A6600": max(travel * inflation * shock(0.06), 0),
    }


def _revenue_for_actual(
    profile: CostCenterProfile,
    month: pd.Timestamp,
    month_index: int,
    rng: np.random.Generator,
) -> float:
    if profile.base_monthly_revenue <= 0:
        return 0.0
    trend = (1 + profile.annual_growth) ** (month_index / 12)
    seasonality = _seasonality(profile, month.month)
    macro = 1.0 + 0.018 * math.sin(month_index / 3.7) - 0.012 * math.cos(month_index / 5.1)
    if month >= pd.Timestamp("2026-01-01"):
        macro *= 0.985 if profile.business_unit == "Retail Stores" else 1.015
    noise = float(rng.lognormal(mean=-0.002, sigma=0.027))
    return profile.base_monthly_revenue * 3.25 * trend * seasonality * macro * noise


def build_actuals(
    rng: np.random.Generator,
    calendar: pd.DataFrame,
    cost_centers: pd.DataFrame,
    headcount: pd.DataFrame,
    capex: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict] = []
    profiles = {profile.cost_center_id: profile for profile in _profiles()}
    actual_months = calendar.loc[calendar["IsActual"], "Date"].tolist()
    hc_lookup = (
        headcount[headcount["Version"] == "Actual"]
        .set_index(["Month", "CostCenterID"])
        .to_dict("index")
    )
    dep_lookup = (
        capex[capex["Version"] == "Actual"]
        .groupby(["Month", "CostCenterID"], as_index=False)["DepreciationTRY"]
        .sum()
        .set_index(["Month", "CostCenterID"])["DepreciationTRY"]
        .to_dict()
    )

    for month_index, month in enumerate(actual_months):
        month_rows: list[dict] = []
        for _, cc in cost_centers.iterrows():
            profile = profiles[cc["CostCenterID"]]
            revenue = _revenue_for_actual(profile, month, month_index, rng)
            base = {
                "Month": month,
                "CostCenterID": profile.cost_center_id,
                "Department": profile.department,
                "BusinessUnit": profile.business_unit,
                "Region": profile.region,
                "Version": "Actual",
                "PeriodStatus": "Actual",
                "SourceSystem": "Synthetic ERP",
            }
            if revenue > 0:
                month_rows.append(
                    {**base, "AccountKey": REVENUE_ACCOUNT_BY_BU[profile.business_unit], "AmountTRY": round(revenue, 2)}
                )
                cogs_shock = float(rng.normal(1.0, 0.008))
                month_rows.extend(
                    [
                        {**base, "AccountKey": "A5000", "AmountTRY": round(revenue * profile.product_cost_ratio * cogs_shock, 2)},
                        {**base, "AccountKey": "A5010", "AmountTRY": round(revenue * profile.fee_ratio * float(rng.normal(1.0, 0.01)), 2)},
                        {**base, "AccountKey": "A5020", "AmountTRY": round(revenue * profile.fulfillment_ratio * float(rng.normal(1.0, 0.012)), 2)},
                    ]
                )

            hc = hc_lookup[(month, profile.cost_center_id)]
            month_rows.extend(
                [
                    {**base, "AccountKey": "A6000", "AmountTRY": float(hc["PayrollCostTRY"])},
                    {**base, "AccountKey": "A6010", "AmountTRY": float(hc["BenefitsCostTRY"])},
                ]
            )
            for account_key, amount in _fixed_opex(profile, month, revenue, rng).items():
                if amount > 0:
                    month_rows.append({**base, "AccountKey": account_key, "AmountTRY": round(amount, 2)})
            depreciation = dep_lookup.get((month, profile.cost_center_id), 0.0)
            if depreciation > 0:
                month_rows.append({**base, "AccountKey": "A6700", "AmountTRY": round(depreciation, 2)})
            if profile.cost_center_id == "CC-801":
                interest = 420_000 * (1.06 ** max(month.year - 2023, 0))
                month_rows.append({**base, "AccountKey": "A6800", "AmountTRY": round(interest, 2)})

        temp = pd.DataFrame(month_rows)
        group = temp.groupby("AccountKey")["AmountTRY"].sum()
        revenue_total = group.reindex(["A4000", "A4010", "A4020", "A4030"], fill_value=0).sum()
        cogs_total = group.reindex(["A5000", "A5010", "A5020"], fill_value=0).sum()
        opex_total = group.reindex(
            ["A6000", "A6010", "A6100", "A6200", "A6300", "A6400", "A6500", "A6600"],
            fill_value=0,
        ).sum()
        depreciation_total = float(group.get("A6700", 0))
        interest_total = float(group.get("A6800", 0))
        taxable_income = revenue_total - cogs_total - opex_total - depreciation_total - interest_total
        tax = max(taxable_income, 0) * 0.25
        corporate = cost_centers[cost_centers["CostCenterID"] == "CC-801"].iloc[0]
        month_rows.append(
            {
                "Month": month,
                "CostCenterID": "CC-801",
                "Department": corporate["Department"],
                "BusinessUnit": corporate["BusinessUnit"],
                "Region": corporate["Region"],
                "Version": "Actual",
                "PeriodStatus": "Actual",
                "SourceSystem": "Synthetic ERP",
                "AccountKey": "A6900",
                "AmountTRY": round(tax, 2),
            }
        )
        rows.extend(month_rows)
    return pd.DataFrame(rows)


def build_budget(
    rng: np.random.Generator,
    actuals: pd.DataFrame,
    accounts: pd.DataFrame,
    cost_centers: pd.DataFrame,
    headcount: pd.DataFrame,
    capex: pd.DataFrame,
) -> pd.DataFrame:
    profiles = {profile.cost_center_id: profile for profile in _profiles()}
    account_group = accounts.set_index("AccountKey")["AccountGroup"].to_dict()
    actual_lookup = (
        actuals.assign(PriorMonth=actuals["Month"] + pd.DateOffset(years=1))
        .set_index(["PriorMonth", "CostCenterID", "AccountKey"])["AmountTRY"]
        .to_dict()
    )
    hc_lookup = (
        headcount[headcount["Version"] == "Budget"]
        .set_index(["Month", "CostCenterID"])
        .to_dict("index")
    )
    dep_lookup = (
        capex[capex["Version"] == "Budget"]
        .groupby(["Month", "CostCenterID"], as_index=False)["DepreciationTRY"]
        .sum()
        .set_index(["Month", "CostCenterID"])["DepreciationTRY"]
        .to_dict()
    )
    budget_months = pd.date_range(BUDGET_START, BUDGET_END, freq="MS")
    rows: list[dict] = []
    for month in budget_months:
        month_rows: list[dict] = []
        for _, cc in cost_centers.iterrows():
            profile = profiles[cc["CostCenterID"]]
            base = {
                "Month": month,
                "CostCenterID": profile.cost_center_id,
                "Department": profile.department,
                "BusinessUnit": profile.business_unit,
                "Region": profile.region,
                "Version": "Budget",
                "PeriodStatus": "Budget",
                "SourceSystem": "FY2026 Budget v1",
            }
            revenue = 0.0
            if profile.base_monthly_revenue > 0:
                prior_revenue = float(
                    actual_lookup.get(
                        (month, profile.cost_center_id, REVENUE_ACCOUNT_BY_BU[profile.business_unit]),
                        0,
                    )
                )
                growth_target = {
                    "Digital Commerce": 1.165,
                    "Retail Stores": 1.105,
                    "Wholesale": 1.125,
                    "Subscription Services": 1.205,
                }[profile.business_unit]
                revenue = prior_revenue * growth_target
                month_rows.append(
                    {**base, "AccountKey": REVENUE_ACCOUNT_BY_BU[profile.business_unit], "AmountTRY": round(revenue, 2)}
                )
                month_rows.extend(
                    [
                        {**base, "AccountKey": "A5000", "AmountTRY": round(revenue * max(profile.product_cost_ratio - 0.006, 0.15), 2)},
                        {**base, "AccountKey": "A5010", "AmountTRY": round(revenue * max(profile.fee_ratio - 0.001, 0.008), 2)},
                        {**base, "AccountKey": "A5020", "AmountTRY": round(revenue * max(profile.fulfillment_ratio - 0.001, 0.012), 2)},
                    ]
                )
            hc = hc_lookup[(month, profile.cost_center_id)]
            month_rows.extend(
                [
                    {**base, "AccountKey": "A6000", "AmountTRY": float(hc["PayrollCostTRY"])},
                    {**base, "AccountKey": "A6010", "AmountTRY": float(hc["BenefitsCostTRY"])},
                ]
            )
            for account_key in ("A6100", "A6200", "A6300", "A6400", "A6500", "A6600"):
                prior = float(actual_lookup.get((month, profile.cost_center_id, account_key), 0))
                if account_key == "A6100" and revenue > 0:
                    prior = max(prior * 1.08, revenue * (0.048 if profile.business_unit == "Digital Commerce" else 0.019))
                else:
                    prior *= 1.115
                if prior > 0:
                    month_rows.append({**base, "AccountKey": account_key, "AmountTRY": round(prior, 2)})
            depreciation = dep_lookup.get((month, profile.cost_center_id), 0.0)
            if depreciation > 0:
                month_rows.append({**base, "AccountKey": "A6700", "AmountTRY": round(depreciation, 2)})
            if profile.cost_center_id == "CC-801":
                prior_interest = float(actual_lookup.get((month, profile.cost_center_id, "A6800"), 0))
                month_rows.append({**base, "AccountKey": "A6800", "AmountTRY": round(prior_interest * 0.96, 2)})

        temp = pd.DataFrame(month_rows)
        totals = temp.assign(AccountGroup=temp["AccountKey"].map(account_group)).groupby("AccountGroup")["AmountTRY"].sum()
        ebt = (
            float(totals.get("Revenue", 0))
            - float(totals.get("COGS", 0))
            - float(totals.get("Operating Expense", 0))
            - float(totals.get("Depreciation", 0))
            - float(totals.get("Interest", 0))
        )
        tax = max(ebt, 0) * 0.25
        corporate = cost_centers[cost_centers["CostCenterID"] == "CC-801"].iloc[0]
        month_rows.append(
            {
                "Month": month,
                "CostCenterID": "CC-801",
                "Department": corporate["Department"],
                "BusinessUnit": corporate["BusinessUnit"],
                "Region": corporate["Region"],
                "Version": "Budget",
                "PeriodStatus": "Budget",
                "SourceSystem": "FY2026 Budget v1",
                "AccountKey": "A6900",
                "AmountTRY": round(tax, 2),
            }
        )
        rows.extend(month_rows)
    return pd.DataFrame(rows)


def build_operational_drivers(
    rng: np.random.Generator,
    actuals: pd.DataFrame,
    budget: pd.DataFrame,
    accounts: pd.DataFrame,
) -> pd.DataFrame:
    revenue_accounts = set(
        accounts.loc[accounts["AccountGroup"] == "Revenue", "AccountKey"]
    )
    rows: list[dict] = []
    for version, frame in (("Actual", actuals), ("Budget", budget)):
        grouped = (
            frame[frame["AccountKey"].isin(revenue_accounts)]
            .groupby(["Month", "BusinessUnit"], as_index=False)["AmountTRY"]
            .sum()
        )
        for _, row in grouped.iterrows():
            bu = row["BusinessUnit"]
            revenue = float(row["AmountTRY"])
            base_price = {
                "Digital Commerce": 1_950,
                "Retail Stores": 2_250,
                "Wholesale": 1_420,
                "Subscription Services": 420,
            }[bu]
            price_trend = (1.012 ** ((pd.Timestamp(row["Month"]).year - 2023) * 12 + pd.Timestamp(row["Month"]).month - 1))
            asp = base_price * price_trend * float(rng.normal(1.0, 0.01))
            transactions = max(int(round(revenue / asp)), 1)
            customers = max(int(round(transactions / (1.25 if bu == "Subscription Services" else 1.12))), 1)
            visits = max(int(round(customers / (0.043 if bu == "Digital Commerce" else 0.11))), 1)
            conversion = customers / visits
            rows.append(
                {
                    "Month": row["Month"],
                    "BusinessUnit": bu,
                    "Version": version,
                    "RevenueTRY": round(revenue, 2),
                    "Transactions": transactions,
                    "AverageSellingPriceTRY": round(asp, 2),
                    "ActiveCustomers": customers,
                    "TrafficOrLeads": visits,
                    "ConversionRate": round(conversion, 5),
                    "RefundOrChurnRate": round(
                        0.035 if bu == "Digital Commerce" else 0.018 if bu != "Subscription Services" else 0.062,
                        4,
                    ),
                }
            )
    return pd.DataFrame(rows)


def build_budget_submissions(cost_centers: pd.DataFrame) -> pd.DataFrame:
    statuses = [
        "Approved",
        "Approved",
        "Approved with Actions",
        "Approved",
        "Approved",
        "Approved",
        "Approved with Actions",
        "Approved",
        "Approved",
        "Approved with Actions",
        "Approved",
        "Approved",
    ]
    rows = []
    for idx, (_, cc) in enumerate(cost_centers.iterrows()):
        submitted = pd.Timestamp("2025-10-06") + pd.Timedelta(days=idx * 2)
        review_rounds = 1 + (idx % 3)
        approved = submitted + pd.Timedelta(days=7 + review_rounds * 3)
        rows.append(
            {
                "CostCenterID": cc["CostCenterID"],
                "CostCenterName": cc["CostCenterName"],
                "Department": cc["Department"],
                "BudgetOwner": cc["BudgetOwner"],
                "BudgetVersion": "FY2026 Budget v1",
                "Status": statuses[idx],
                "SubmittedDate": submitted,
                "ApprovalDate": approved,
                "ReviewRounds": review_rounds,
                "ControllerComment": (
                    "Phasing adjusted and approved"
                    if "Actions" in statuses[idx]
                    else "Approved within planning guardrails"
                ),
            }
        )
    return pd.DataFrame(rows)


def generate_all() -> dict[str, pd.DataFrame]:
    _ensure_dirs()
    rng = np.random.default_rng(RANDOM_SEED)
    calendar = build_calendar()
    accounts = build_accounts()
    cost_centers = build_cost_centers()
    scenarios = build_scenarios()
    headcount = build_headcount(rng, calendar, cost_centers)
    projects, capex = build_capex(calendar)
    actuals = build_actuals(rng, calendar, cost_centers, headcount, capex)
    budget = build_budget(rng, actuals, accounts, cost_centers, headcount, capex)
    drivers = build_operational_drivers(rng, actuals, budget, accounts)
    submissions = build_budget_submissions(cost_centers)
    metadata = pd.DataFrame(
        [
            ("Company", COMPANY_NAME),
            ("AsOfDate", AS_OF_DATE),
            ("Currency", "TRY"),
            ("DataClassification", "Synthetic portfolio data"),
            ("ActualCoverage", f"{ACTUAL_START} to {ACTUAL_END}"),
            ("BudgetCoverage", f"{BUDGET_START} to {BUDGET_END}"),
            ("RollingForecastCoverage", f"2026-07-01 to {ROLLING_FORECAST_END}"),
            ("Owner", "Murat Miraç Gedik"),
        ],
        columns=["MetadataKey", "MetadataValue"],
    )

    datasets = {
        "dim_calendar": calendar,
        "dim_account": accounts,
        "dim_cost_center": cost_centers,
        "dim_scenario": scenarios,
        "dim_capex_project": projects,
        "fact_actuals": actuals,
        "fact_budget": budget,
        "fact_headcount": headcount,
        "fact_capex": capex,
        "fact_operational_drivers": drivers,
        "budget_submissions": submissions,
        "project_metadata": metadata,
    }
    for name, frame in datasets.items():
        frame.to_csv(DATA_DIR / f"{name}.csv", index=False, date_format="%Y-%m-%d")
    return datasets


if __name__ == "__main__":
    result = generate_all()
    for dataset_name, frame in result.items():
        print(f"{dataset_name}: {len(frame):,} rows")
