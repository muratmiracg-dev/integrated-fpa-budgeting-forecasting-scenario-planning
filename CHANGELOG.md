# Changelog

## Unreleased

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
