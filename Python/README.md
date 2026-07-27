# Python Planning Engine

## Modules

| Module | Responsibility |
|---|---|
| `data_generation.py` | Synthetic dimensions, actuals, and operating data |
| `planning.py` | Budget, working capital, cash, workforce, and capex |
| `forecasting.py` | Candidate models, backtesting, and champion selection |
| `scenarios.py` | Scenario engine and Monte Carlo simulation |
| `reporting.py` | Management reporting tables and decision insights |
| `database.py` | SQLite database creation |
| `validation.py` | Financial, coverage, governance, and quality controls |
| `run_pipeline.py` | End-to-end orchestration |

Run the pipeline from the repository root:

```bash
PYTHONPATH=Python/src python -m fpa_system.run_pipeline
```

Run tests:

```bash
PYTHONPATH=Python/src pytest -q
```
