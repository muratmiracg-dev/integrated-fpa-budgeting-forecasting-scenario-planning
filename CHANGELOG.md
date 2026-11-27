# Changelog

## Unreleased

- Scenario tax was charged at 25% of each month's positive EBT, ignoring loss months. The
  Stress scenario has nine loss-making forecast months, so it paid tax across a loss-making
  forecast window. Tax is now accrued on year-to-date EBT per fiscal year. Stress net income
  is TRY 37.6m (was TRY 35.4m) and its ending cash TRY 118.1m (was TRY 115.9m). Other
  scenarios move by cents of rounding. The Excel, deck, PBIP and PDF deliverables still show
  the earlier Stress figures until they are rebuilt.
- Revenue-forecast bands were sized by the standard deviation of the champion's hold-out
  errors, which removes their mean, although the bands are centred on the unadjusted forecast.
  Retail Stores' champion over-forecast all six hold-out months (mean error TRY 1.01m), so its
  band used TRY 0.76m instead of the TRY 1.23m root-mean-square error and was 38% too narrow.
  Bands now use the back-test RMSE; `ResidualStdTRY` is replaced by `BacktestRMSETRY` in
  `revenue_forecast.csv` (Digital Commerce x1.09, Retail Stores x1.61, Subscription x0.97,
  Wholesale x0.93). Point forecasts are unchanged.
- CI now checks that the committed `Data/` tables and `SQL/integrated_fpa_analytics.db` are what
  the current code produces. The rebuild step rewrote `Data/` before the tests, so tests such as
  the committed-variance check only ever saw fresh output and a stale commit stayed green. CI
  keeps a copy of the committed outputs, rebuilds, and runs `Tools/compare_outputs.py` (CSV and
  JSON values within relative 1e-9, SQLite schema and rows). Two tests cover the comparator.
- Added `Python/tests/test_pnl_and_variance.py` (10 tests). Until now the P&L cascade, margins and
  budget-variance favourability were only exercised indirectly by the pipeline. The tests cover
  known-answer cascades, zero-revenue margins, favourable/unfavourable direction for revenue and
  cost lines, negative and zero comparators, the cascade identities in `Data/monthly_pnl.csv`, and
  that `Data/variance_analysis.csv` matches the reporting code.

## v1.0.0 — 2026-07-26

- Added 42 months of synthetic actuals, FY2026 budget, and 18-month rolling forecast.
- Added P&L, cash-flow, working-capital, headcount, capex, business-unit, and departmental models.
- Added four forecast algorithms, backtesting, champion selection, and model governance.
- Added four operating scenarios and 5,000-trial Monte Carlo analysis.
- Added SQLite schema, analytics views, sample queries, and generated database.
- Added 31-sheet professional Excel FP&A workbook.
- Added 11-page Power BI PBIP report and reusable DAX catalog.
- Added English and Turkish 20-slide executive presentations.
- Added 12-page vector HD executive PDF and 1080p portfolio images.
- Added automated controls, tests, CI workflow, documentation, and publishing guidance.
