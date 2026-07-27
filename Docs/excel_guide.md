# Excel FP&A Model Guide

## Open the workbook

Open:

`Excel/Integrated_FP&A_Budgeting_Forecasting_Scenario_Planning_Model.xlsx`

The file is a formula-driven planning and scenario workbook. It contains 31 sheets and uses TRY millions for management-facing views.

## Recommended review order

1. `Cover`
2. `Executive Dashboard`
3. `Scenario Control`
4. `Income Statement`
5. `Budget vs Actual`
6. `Rolling Forecast`
7. `Cash Flow`
8. `Working Capital`
9. `Headcount Plan`
10. `Capex Plan`
11. `Forecast Accuracy`
12. `Risk Analysis`
13. `Assumptions`
14. `Checks`

## Input and formula conventions

- Blue/yellow cells: planning inputs or selectors
- Green cells: formulas and cross-sheet links
- Dark headers: fixed model structure
- TRY values in management views: millions
- Percentages: decimal calculations displayed as percentages

## Scenario use

Select the scenario on `Scenario Control`. Review its impact on revenue, EBITDA, margin, cash, and working capital. Scenario outputs are based on the project’s governed scenario tables; they do not overwrite the source data.

## Controls

The `Checks` sheet reports 11 visible workbook controls. All are expected to display `PASS`. The project-level Python validation contains 17 broader controls.

## Refresh

The workbook is delivered with populated source sheets. If the underlying CSV outputs are regenerated, rerun:

```bash
node Tools/build_excel.mjs .
```

This rebuilds the workbook and preserves the professional formatting and formulas.
