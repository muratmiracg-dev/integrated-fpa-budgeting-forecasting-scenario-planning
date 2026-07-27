# Quality Assurance

## Automated financial controls

The generated validation report contains **17 passing checks out of 17**.

| Category | Checks |
|---|---|
| Coverage | Actual, budget, and rolling-forecast periods |
| Referential integrity | Accounts and cost centers |
| Financial integrity | P&L identities, net income, cash roll-forward, working capital |
| Scenario engine | Revenue and EBITDA hierarchy |
| Forecasting | One champion per business unit, accuracy threshold |
| Governance | All budget-owner submissions approved |
| Capex | Non-negative spend, depreciation, and NBV |
| Risk | 5,000 finite Monte Carlo trials |

## Unit tests

`Python/tests/test_financial_controls.py` checks:

- actual history coverage
- P&L equation reconciliation
- cash-flow roll-forward
- scenario ordering
- champion forecast selection

## Artifact validation

- Excel: formula-error scan returns zero formula errors.
- Excel: 11 of 11 visible workbook checks pass.
- Power BI: 11 pages, 89 visuals, valid JSON definitions, no unknown model entity references.
- PowerPoint: 20 slides in English and 20 slides in Turkish; overflow tests pass.
- PDF: 12 vector pages; embedded fonts; 1920×1080 render verification.

## Continuous integration

`.github/workflows/ci.yml` installs dependencies, runs Ruff, rebuilds the analytical pipeline, and runs Pytest on pushes and pull requests to `main`.

## Known boundaries

The data is synthetic. The project validates the architecture, calculations, controls, and reporting workflow, not the operational accuracy of a real company’s plan.
