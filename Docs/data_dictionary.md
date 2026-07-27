# Data Dictionary

## Dimensions

| File | Grain | Purpose |
|---|---|---|
| `dim_calendar.csv` | One row per month | Date, month, quarter, year, fiscal labels |
| `dim_account.csv` | One row per account | Chart of accounts and P&L classification |
| `dim_cost_center.csv` | One row per cost center | Department, business unit, region, owner |
| `dim_scenario.csv` | One row per scenario | Scenario assumptions and display order |
| `dim_capex_project.csv` | One row per project | Capex category, owner, timing, useful life |

## Core fact tables

| File | Grain | Key measures |
|---|---|---|
| `fact_actuals.csv` | Month × cost center × account | Actual amount |
| `fact_budget.csv` | Month × cost center × account | Budget amount |
| `fact_forecast.csv` | Month × cost center × account | Rolling-forecast amount |
| `fact_scenario.csv` | Scenario × month × cost center × account | Scenario amount |
| `fact_operational_drivers.csv` | Month × business unit × version | Revenue, transactions, ASP, traffic, conversion, churn |
| `fact_working_capital.csv` | Month × version | DSO, DIO, DPO, AR, inventory, AP, NWC |
| `fact_cash_flow.csv` | Month × version | CFO, capex, financing, net cash flow, cash balances |
| `fact_headcount.csv` | Month × department × version | FTE, hires, exits, payroll, benefits |
| `fact_capex.csv` | Month × project × version | Spend, depreciation, remaining NBV |

## Reporting tables

| File | Purpose |
|---|---|
| `monthly_pnl.csv` | Monthly consolidated P&L by version |
| `annual_pnl.csv` | Annual and partial-year consolidated P&L |
| `variance_analysis.csv` | Actual/forecast comparisons against budget and prior year |
| `department_performance.csv` | Department P&L |
| `business_unit_performance.csv` | Business-unit P&L |
| `monthly_kpi_dashboard.csv` | Joined management KPI view |
| `scenario_summary.csv` | Scenario revenue, margin, cash, and CCC |
| `risk_summary.csv` | P10/P50/P90 and downside probabilities |
| `forecast_model_comparison.csv` | Candidate-model metrics and champion flag |
| `forecast_backtest.csv` | Observation-level backtest results |
| `forecast_bridge.csv` | Budget-to-forecast EBITDA bridge |
| `management_insights.csv` | Evidence, action, and owner mapping |

## Version and period fields

- `Version`: Actual, Budget, Forecast, or scenario name.
- `PeriodStatus`: Actual, Budget, or Forecast status for a specific month.
- `MonthKey`: sortable `YYYY-MM` key.
- `SourceSystem`: synthetic source lineage.

## Currency and rates

- Monetary fields end in `TRY` and are stored in Turkish lira.
- Percentage fields are stored as decimals; for example `0.0918` represents `9.18%`.
- Days metrics are stored as numeric day values.
