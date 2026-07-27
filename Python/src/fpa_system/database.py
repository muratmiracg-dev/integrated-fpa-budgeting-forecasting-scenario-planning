from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .config import DATA_DIR, SQL_DIR


def build_database(db_path: Path | None = None) -> Path:
    SQL_DIR.mkdir(parents=True, exist_ok=True)
    db_path = db_path or SQL_DIR / "integrated_fpa_analytics.db"
    if db_path.exists():
        db_path.unlink()
    csv_files = sorted(DATA_DIR.glob("*.csv"))
    with sqlite3.connect(db_path) as connection:
        for path in csv_files:
            frame = pd.read_csv(path)
            frame.to_sql(path.stem, connection, if_exists="replace", index=False)
        connection.executescript(
            """
            CREATE INDEX idx_actuals_month_account
                ON fact_actuals (Month, AccountKey);
            CREATE INDEX idx_budget_month_account
                ON fact_budget (Month, AccountKey);
            CREATE INDEX idx_forecast_month_account
                ON fact_forecast (Month, AccountKey);
            CREATE INDEX idx_actuals_cost_center
                ON fact_actuals (CostCenterID, Department, BusinessUnit);
            CREATE INDEX idx_scenario_month
                ON fact_scenario (Scenario, Month);

            CREATE VIEW vw_monthly_actual_pnl AS
            SELECT
                a.Month,
                SUM(CASE WHEN d.AccountGroup = 'Revenue' THEN a.AmountTRY ELSE 0 END) AS RevenueTRY,
                SUM(CASE WHEN d.AccountGroup = 'COGS' THEN a.AmountTRY ELSE 0 END) AS COGSTRY,
                SUM(CASE WHEN d.AccountGroup = 'Operating Expense' THEN a.AmountTRY ELSE 0 END) AS OperatingExpenseTRY,
                SUM(CASE WHEN d.AccountGroup = 'Depreciation' THEN a.AmountTRY ELSE 0 END) AS DepreciationTRY,
                SUM(CASE WHEN d.AccountGroup = 'Interest' THEN a.AmountTRY ELSE 0 END) AS InterestTRY,
                SUM(CASE WHEN d.AccountGroup = 'Tax' THEN a.AmountTRY ELSE 0 END) AS TaxTRY
            FROM fact_actuals a
            JOIN dim_account d ON d.AccountKey = a.AccountKey
            GROUP BY a.Month;

            CREATE VIEW vw_fy2026_department_variance AS
            WITH forecast AS (
                SELECT Department, SUM(EBITDATRY) AS ForecastEBITDATRY
                FROM department_performance
                WHERE Version = 'Forecast' AND Year = 2026
                GROUP BY Department
            ),
            budget AS (
                SELECT Department, SUM(EBITDATRY) AS BudgetEBITDATRY
                FROM department_performance
                WHERE Version = 'Budget' AND Year = 2026
                GROUP BY Department
            )
            SELECT
                f.Department,
                f.ForecastEBITDATRY,
                b.BudgetEBITDATRY,
                f.ForecastEBITDATRY - b.BudgetEBITDATRY AS VarianceTRY
            FROM forecast f
            JOIN budget b ON b.Department = f.Department;

            CREATE VIEW vw_scenario_decision_summary AS
            SELECT
                Scenario,
                RevenueTRY,
                EBITDATRY,
                EBITDAMarginPct,
                EndingCashTRY,
                MinimumCashTRY,
                CashConversionCycleDays
            FROM scenario_summary
            ORDER BY ScenarioOrder;
            """
        )
    return db_path


if __name__ == "__main__":
    print(build_database())
