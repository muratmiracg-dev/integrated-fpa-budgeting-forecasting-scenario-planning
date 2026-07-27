# Power BI PBIP Guide

## Open the project

Open:

`PowerBI/Integrated_FPA_PBIP/Integrated_FPA_Planning_Analytics.pbip`

Use a current version of Power BI Desktop that supports Power BI Project (`.pbip`) files.

## Data portability

The semantic model embeds the synthetic sample data as Base64-encoded CSV content in Power Query. No local CSV path remapping is required.

## Model

- 9 semantic-model tables
- 3 relationships
- 40 reusable measures
- Calendar-centered one-to-many relationships
- Single-direction filtering
- Dedicated P&L-stage table

## Report pages

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

## DAX

The standalone measure catalog is available at:

`PowerBI/Integrated_FPA_Measures.dax`

It includes revenue, budget, gross profit, opex, EBITDA, EBIT, net income, cash, headcount, CCC, margins, attainment, prior-year, YoY, variance, department, business-unit, P&L-stage, and scenario measures.

## Packaged download

If GitHub does not preserve the folder download experience, use:

`PowerBI/Integrated_FPA_Planning_PBIP.zip`

Extract the ZIP completely before opening the `.pbip` file.
