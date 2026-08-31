# Methodology and Architecture

## Planning horizon

- Actuals: January 2023–June 2026
- FY2026 budget: January–December 2026
- Rolling forecast: January 2026–June 2027
- Closed actual period in the rolling forecast: January–June 2026
- Forward forecast period: July 2026–June 2027

## Analytical flow

1. `data_generation.py` creates dimensional and transaction-level synthetic source data.
2. `planning.py` builds the annual budget, workforce plan, capex schedule, working-capital plan, and cash flow.
3. `forecasting.py` trains and backtests candidate revenue models by business unit.
4. `scenarios.py` applies coherent operating assumptions and runs 5,000 Monte Carlo simulations.
5. `reporting.py` produces management-ready P&L, variance, departmental, business-unit, KPI, and risk tables.
6. `database.py` writes the SQLite analytical database.
7. `validation.py` reconciles financial identities, coverage, relationships, governance, and simulation output.

## Data model

The design uses conformed dimensions for calendar, accounts, cost centers, scenarios, and capex projects. Fact tables preserve month, version, period status, business unit, department, region, and source system where applicable.

The Power BI semantic layer uses a calendar-centered star design. Relationships are one-to-many with single-direction filtering. Measures are separated from raw columns and stored in a reusable DAX catalog.

## Financial statement logic

The core P&L follows:

```text
Revenue
− COGS
= Gross Profit
− Operating Expense
= EBITDA
− Depreciation
= EBIT
− Interest
= EBT
− Tax
= Net Income
```

Cash is rolled forward from beginning cash through cash from operations, capex, financing, and other cash movements. Net working capital is calculated as accounts receivable plus inventory less accounts payable.

Before P&L aggregation, the pipeline enforces a many-to-one account mapping contract. Every ledger row must resolve to exactly one chart-of-accounts entry, account keys must be unique in the dimension, and monetary amounts must be finite numeric values. The pipeline fails fast instead of silently excluding malformed or unmapped ledger rows.

## Forecast methodology

Candidate models include:

- Seasonal Naive
- Linear Trend + Seasonality
- Log-Ridge Seasonal
- Gradient Boosting

Models are backtested using MAE, RMSE, WAPE, bias, and a combined score. A single champion is selected for each business unit. Closed actual months are not overwritten by forecast values.

## Scenario methodology

Upside, Base, Downside, and Stress cases change connected assumptions for revenue, price/mix, gross margin, opex, working capital, capex, and cash. The resulting scenarios remain internally consistent across P&L and liquidity.

## Risk simulation

Monte Carlo trials sample uncertainty around revenue, margin, expenses, and working-capital conditions. Output is summarized through P10, P50, P90, downside probabilities, and ending-cash distributions.

## Reproducibility

Run:

```bash
PYTHONPATH=Python/src python -m fpa_system.run_pipeline
```

The command regenerates source data, forecasts, planning outputs, the SQLite database, and the validation report.
