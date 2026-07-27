from __future__ import annotations

import json

from .data_generation import generate_all
from .database import build_database
from .forecasting import run_forecasting
from .planning import build_rolling_forecast, build_working_capital_and_cash_flow
from .reporting import build_reporting_tables
from .scenarios import build_scenarios, run_monte_carlo
from .validation import validate_project


def main() -> None:
    generated = generate_all()
    forecast, model_comparison, backtest = run_forecasting()
    rolling = build_rolling_forecast()
    working_capital, cash_flow = build_working_capital_and_cash_flow()
    scenario_fact, scenario_monthly, scenario_summary = build_scenarios()
    simulations, risk_summary = run_monte_carlo()
    reporting = build_reporting_tables()
    database_path = build_database()
    validation = validate_project()
    payload = {
        "generated_tables": {name: len(frame) for name, frame in generated.items()},
        "revenue_forecast_rows": len(forecast),
        "model_comparison_rows": len(model_comparison),
        "backtest_rows": len(backtest),
        "rolling_forecast_rows": len(rolling),
        "working_capital_rows": len(working_capital),
        "cash_flow_rows": len(cash_flow),
        "scenario_fact_rows": len(scenario_fact),
        "scenario_monthly_rows": len(scenario_monthly),
        "scenario_summary_rows": len(scenario_summary),
        "monte_carlo_rows": len(simulations),
        "risk_summary_rows": len(risk_summary),
        "reporting_tables": {name: len(frame) for name, frame in reporting.items()},
        "database": str(database_path),
        "validation_passed": validation["all_passed"],
        "validation_checks": (
            f"{validation['passed_checks']}/{validation['total_checks']}"
        ),
    }
    print(json.dumps(payload, indent=2))
    if not validation["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
