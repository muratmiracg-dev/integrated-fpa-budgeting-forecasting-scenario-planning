from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ACTUAL_END, DATA_DIR, REVENUE_ACCOUNT_BY_BU, ROLLING_FORECAST_END

P_AND_L_GROUPS = (
    "Revenue",
    "COGS",
    "Operating Expense",
    "Depreciation",
    "Interest",
    "Tax",
)


def aggregate_pnl(
    fact: pd.DataFrame,
    accounts: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    enriched = fact.merge(
        accounts[["AccountKey", "AccountGroup"]], on="AccountKey", how="left"
    )
    grouped = (
        enriched.groupby(group_columns + ["AccountGroup"], as_index=False)["AmountTRY"]
        .sum()
        .pivot_table(
            index=group_columns,
            columns="AccountGroup",
            values="AmountTRY",
            fill_value=0,
        )
        .reset_index()
    )
    grouped.columns.name = None
    for column in P_AND_L_GROUPS:
        if column not in grouped.columns:
            grouped[column] = 0.0
    grouped["GrossProfitTRY"] = grouped["Revenue"] - grouped["COGS"]
    grouped["EBITDATRY"] = grouped["GrossProfitTRY"] - grouped["Operating Expense"]
    grouped["EBITTRY"] = grouped["EBITDATRY"] - grouped["Depreciation"]
    grouped["EBTTRY"] = grouped["EBITTRY"] - grouped["Interest"]
    grouped["NetIncomeTRY"] = grouped["EBTTRY"] - grouped["Tax"]
    grouped["GrossMarginPct"] = grouped["GrossProfitTRY"] / grouped["Revenue"].replace(0, np.nan)
    grouped["EBITDAMarginPct"] = grouped["EBITDATRY"] / grouped["Revenue"].replace(0, np.nan)
    grouped["NetIncomeMarginPct"] = grouped["NetIncomeTRY"] / grouped["Revenue"].replace(0, np.nan)
    return grouped.rename(
        columns={
            "Revenue": "RevenueTRY",
            "COGS": "COGSTRY",
            "Operating Expense": "OperatingExpenseTRY",
            "Depreciation": "DepreciationTRY",
            "Interest": "InterestTRY",
            "Tax": "TaxTRY",
        }
    )


def build_rolling_forecast() -> pd.DataFrame:
    actuals = pd.read_csv(DATA_DIR / "fact_actuals.csv", parse_dates=["Month"])
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    cost_centers = pd.read_csv(DATA_DIR / "dim_cost_center.csv")
    headcount = pd.read_csv(DATA_DIR / "fact_headcount.csv", parse_dates=["Month"])
    capex = pd.read_csv(DATA_DIR / "fact_capex.csv", parse_dates=["Month"])
    revenue_forecast = pd.read_csv(
        DATA_DIR / "revenue_forecast.csv", parse_dates=["Month"]
    )
    account_group = accounts.set_index("AccountKey")["AccountGroup"].to_dict()

    actual_2026 = actuals[
        (actuals["Month"] >= pd.Timestamp("2026-01-01"))
        & (actuals["Month"] <= pd.Timestamp(ACTUAL_END))
    ].copy()
    actual_2026["Version"] = "Forecast"
    actual_2026["PeriodStatus"] = "Actual"
    actual_2026["SourceSystem"] = "Q2 2026 Rolling Forecast - Closed Actual"
    rows = actual_2026.to_dict("records")

    historical_revenue = actuals[
        actuals["AccountKey"].isin(REVENUE_ACCOUNT_BY_BU.values())
    ]
    shares = (
        historical_revenue[historical_revenue["Month"].dt.year == 2025]
        .groupby(["BusinessUnit", "CostCenterID"], as_index=False)["AmountTRY"]
        .sum()
    )
    shares["Share"] = shares["AmountTRY"] / shares.groupby("BusinessUnit")[
        "AmountTRY"
    ].transform("sum")
    share_lookup = shares.set_index(["BusinessUnit", "CostCenterID"])["Share"].to_dict()

    h1 = actuals[
        (actuals["Month"] >= pd.Timestamp("2026-01-01"))
        & (actuals["Month"] <= pd.Timestamp(ACTUAL_END))
    ].copy()
    h1_revenue = (
        h1[h1["AccountKey"].isin(REVENUE_ACCOUNT_BY_BU.values())]
        .groupby("CostCenterID")["AmountTRY"]
        .sum()
        .to_dict()
    )
    h1_account = (
        h1.groupby(["CostCenterID", "AccountKey"])["AmountTRY"].sum().to_dict()
    )
    ratio_lookup: dict[tuple[str, str], float] = {}
    for (cost_center, account_key), value in h1_account.items():
        revenue = h1_revenue.get(cost_center, 0)
        if revenue > 0 and account_group.get(account_key) in ("COGS", "Operating Expense"):
            ratio_lookup[(cost_center, account_key)] = value / revenue

    base_2025 = (
        actuals[actuals["Month"].dt.year == 2025]
        .groupby(["CostCenterID", "AccountKey"])["AmountTRY"]
        .mean()
        .to_dict()
    )
    hc_lookup = (
        headcount[headcount["Version"] == "Forecast"]
        .set_index(["Month", "CostCenterID"])
        .to_dict("index")
    )
    dep_lookup = (
        capex[capex["Version"] == "Forecast"]
        .groupby(["Month", "CostCenterID"], as_index=False)["DepreciationTRY"]
        .sum()
        .set_index(["Month", "CostCenterID"])["DepreciationTRY"]
        .to_dict()
    )
    forecast_lookup = revenue_forecast.set_index(
        ["Month", "BusinessUnit"]
    )["ForecastRevenueTRY"].to_dict()
    future_months = pd.date_range(
        pd.Timestamp(ACTUAL_END) + pd.DateOffset(months=1),
        pd.Timestamp(ROLLING_FORECAST_END),
        freq="MS",
    )

    for month in future_months:
        month_rows: list[dict] = []
        for _, cc in cost_centers.iterrows():
            cost_center = cc["CostCenterID"]
            business_unit = cc["BusinessUnit"]
            base = {
                "Month": month,
                "CostCenterID": cost_center,
                "Department": cc["Department"],
                "BusinessUnit": business_unit,
                "Region": cc["Region"],
                "Version": "Forecast",
                "PeriodStatus": "Forecast",
                "SourceSystem": "Q2 2026 Rolling Forecast",
            }
            revenue = 0.0
            if business_unit in REVENUE_ACCOUNT_BY_BU:
                business_unit_forecast = float(
                    forecast_lookup[(month, business_unit)]
                )
                revenue = business_unit_forecast * float(
                    share_lookup.get((business_unit, cost_center), 0)
                )
                month_rows.append(
                    {
                        **base,
                        "AccountKey": REVENUE_ACCOUNT_BY_BU[business_unit],
                        "AmountTRY": round(revenue, 2),
                    }
                )
                for account_key in ("A5000", "A5010", "A5020"):
                    historical_ratio = ratio_lookup.get((cost_center, account_key), 0)
                    efficiency = 0.995 if month.year == 2026 else 0.990
                    month_rows.append(
                        {
                            **base,
                            "AccountKey": account_key,
                            "AmountTRY": round(revenue * historical_ratio * efficiency, 2),
                        }
                    )

            hc = hc_lookup[(month, cost_center)]
            month_rows.extend(
                [
                    {**base, "AccountKey": "A6000", "AmountTRY": float(hc["PayrollCostTRY"])},
                    {**base, "AccountKey": "A6010", "AmountTRY": float(hc["BenefitsCostTRY"])},
                ]
            )
            months_from_2025 = (month.year - 2025) * 12 + month.month - 6
            escalation = 1.10 ** (months_from_2025 / 12)
            for account_key in ("A6100", "A6200", "A6300", "A6400", "A6500", "A6600"):
                if revenue > 0 and account_key == "A6100":
                    ratio = ratio_lookup.get((cost_center, account_key), 0.02)
                    value = revenue * ratio * 0.97
                elif revenue > 0 and account_key == "A6200":
                    ratio = ratio_lookup.get((cost_center, account_key), 0.01)
                    value = revenue * ratio
                else:
                    value = float(base_2025.get((cost_center, account_key), 0)) * escalation
                if value > 0:
                    month_rows.append(
                        {**base, "AccountKey": account_key, "AmountTRY": round(value, 2)}
                    )
            depreciation = dep_lookup.get((month, cost_center), 0.0)
            if depreciation > 0:
                month_rows.append(
                    {**base, "AccountKey": "A6700", "AmountTRY": round(depreciation, 2)}
                )
            if cost_center == "CC-801":
                interest = float(base_2025.get((cost_center, "A6800"), 0)) * 0.96
                month_rows.append(
                    {**base, "AccountKey": "A6800", "AmountTRY": round(interest, 2)}
                )

        temp = pd.DataFrame(month_rows)
        totals = temp.assign(
            AccountGroup=temp["AccountKey"].map(account_group)
        ).groupby("AccountGroup")["AmountTRY"].sum()
        ebt = (
            float(totals.get("Revenue", 0))
            - float(totals.get("COGS", 0))
            - float(totals.get("Operating Expense", 0))
            - float(totals.get("Depreciation", 0))
            - float(totals.get("Interest", 0))
        )
        corporate = cost_centers[cost_centers["CostCenterID"] == "CC-801"].iloc[0]
        month_rows.append(
            {
                "Month": month,
                "CostCenterID": "CC-801",
                "Department": corporate["Department"],
                "BusinessUnit": corporate["BusinessUnit"],
                "Region": corporate["Region"],
                "Version": "Forecast",
                "PeriodStatus": "Forecast",
                "SourceSystem": "Q2 2026 Rolling Forecast",
                "AccountKey": "A6900",
                "AmountTRY": round(max(ebt, 0) * 0.25, 2),
            }
        )
        rows.extend(month_rows)

    forecast = pd.DataFrame(rows).sort_values(
        ["Month", "CostCenterID", "AccountKey"]
    )
    forecast.to_csv(
        DATA_DIR / "fact_forecast.csv", index=False, date_format="%Y-%m-%d"
    )
    return forecast


def build_working_capital_and_cash_flow() -> tuple[pd.DataFrame, pd.DataFrame]:
    actuals = pd.read_csv(DATA_DIR / "fact_actuals.csv", parse_dates=["Month"])
    budget = pd.read_csv(DATA_DIR / "fact_budget.csv", parse_dates=["Month"])
    forecast = pd.read_csv(DATA_DIR / "fact_forecast.csv", parse_dates=["Month"])
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    capex = pd.read_csv(DATA_DIR / "fact_capex.csv", parse_dates=["Month"])

    datasets = {
        "Actual": actuals,
        "Budget": budget,
        "Forecast": forecast,
    }
    pnl_frames = []
    for version, fact in datasets.items():
        pnl = aggregate_pnl(fact, accounts, ["Month"])
        pnl["Version"] = version
        pnl_frames.append(pnl)
    pnl_all = pd.concat(pnl_frames, ignore_index=True)

    working_rows: list[dict] = []
    previous_nwc_by_version: dict[str, float] = {}
    actual_nwc_lookup: dict[pd.Timestamp, float] = {}
    for version in ("Actual", "Budget", "Forecast"):
        version_pnl = pnl_all[pnl_all["Version"] == version].sort_values("Month")
        for _, row in version_pnl.iterrows():
            month = pd.Timestamp(row["Month"])
            seasonal = 3 if month.month in (10, 11, 12) else 0
            if version == "Actual":
                t = (month.year - 2023) * 12 + month.month - 1
                dso = 34 - min(t * 0.08, 3.5) + seasonal
                dio = 67 - min(t * 0.12, 5.0) + seasonal * 1.4
                dpo = 45 + min(t * 0.07, 3.0)
            elif version == "Budget":
                dso, dio, dpo = 29 + seasonal * 0.5, 56 + seasonal, 50
            else:
                dso, dio, dpo = 31 + seasonal * 0.7, 60 + seasonal * 1.2, 48
            days = month.days_in_month
            accounts_receivable = float(row["RevenueTRY"]) * dso / days
            inventory = float(row["COGSTRY"]) * dio / days
            accounts_payable = float(row["COGSTRY"]) * dpo / days
            nwc = accounts_receivable + inventory - accounts_payable
            if version == "Actual":
                prior_nwc = previous_nwc_by_version.get(version, nwc)
                actual_nwc_lookup[month] = nwc
            else:
                prior_nwc = previous_nwc_by_version.get(
                    version,
                    actual_nwc_lookup.get(pd.Timestamp("2025-12-01"), nwc),
                )
            change_nwc = nwc - prior_nwc
            previous_nwc_by_version[version] = nwc
            working_rows.append(
                {
                    "Month": month,
                    "Version": version,
                    "DSO": round(dso, 2),
                    "DIO": round(dio, 2),
                    "DPO": round(dpo, 2),
                    "CashConversionCycleDays": round(dso + dio - dpo, 2),
                    "AccountsReceivableTRY": round(accounts_receivable, 2),
                    "InventoryTRY": round(inventory, 2),
                    "AccountsPayableTRY": round(accounts_payable, 2),
                    "NetWorkingCapitalTRY": round(nwc, 2),
                    "ChangeInNWCTRY": round(change_nwc, 2),
                }
            )
    working = pd.DataFrame(working_rows)

    capex_monthly = (
        capex.groupby(["Month", "Version"], as_index=False)["CapexSpendTRY"].sum()
    )
    cash_rows: list[dict] = []
    ending_cash_actual: dict[pd.Timestamp, float] = {}
    for version in ("Actual", "Budget", "Forecast"):
        version_pnl = pnl_all[pnl_all["Version"] == version].sort_values("Month")
        version_wc = working[working["Version"] == version].set_index("Month")
        version_capex = capex_monthly[capex_monthly["Version"] == version].set_index("Month")
        if version == "Actual":
            beginning_cash = 52_000_000.0
        else:
            beginning_cash = ending_cash_actual.get(pd.Timestamp("2025-12-01"), 52_000_000.0)
        for _, row in version_pnl.iterrows():
            month = pd.Timestamp(row["Month"])
            wc = version_wc.loc[month]
            capex_spend = (
                float(version_capex.loc[month, "CapexSpendTRY"])
                if month in version_capex.index
                else 0.0
            )
            cash_from_operations = (
                float(row["EBITDATRY"])
                - float(row["TaxTRY"])
                - float(row["InterestTRY"])
                - float(wc["ChangeInNWCTRY"])
            )
            financing = 0.0
            if version == "Actual" and month == pd.Timestamp("2024-03-01"):
                financing = 30_000_000.0
            elif month.month in (3, 6, 9, 12):
                financing = -2_000_000.0
            net_cash_flow = cash_from_operations - capex_spend + financing
            ending_cash = beginning_cash + net_cash_flow
            cash_rows.append(
                {
                    "Month": month,
                    "Version": version,
                    "BeginningCashTRY": round(beginning_cash, 2),
                    "CashFromOperationsTRY": round(cash_from_operations, 2),
                    "CapitalExpenditureTRY": round(capex_spend, 2),
                    "FinancingCashFlowTRY": round(financing, 2),
                    "NetCashFlowTRY": round(net_cash_flow, 2),
                    "EndingCashTRY": round(ending_cash, 2),
                }
            )
            beginning_cash = ending_cash
            if version == "Actual":
                ending_cash_actual[month] = ending_cash

    cash_flow = pd.DataFrame(cash_rows)
    working.to_csv(
        DATA_DIR / "fact_working_capital.csv", index=False, date_format="%Y-%m-%d"
    )
    cash_flow.to_csv(
        DATA_DIR / "fact_cash_flow.csv", index=False, date_format="%Y-%m-%d"
    )
    return working, cash_flow


if __name__ == "__main__":
    built_forecast = build_rolling_forecast()
    wc, cash = build_working_capital_and_cash_flow()
    print(f"fact_forecast: {len(built_forecast):,} rows")
    print(f"fact_working_capital: {len(wc):,} rows")
    print(f"fact_cash_flow: {len(cash):,} rows")
