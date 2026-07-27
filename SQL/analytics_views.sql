-- Management-reporting views.

CREATE VIEW vw_monthly_actual_pnl AS
SELECT
    a.Month,
    SUM(CASE WHEN d.AccountGroup = 'Revenue' THEN a.AmountTRY ELSE 0 END) AS RevenueTRY,
    SUM(CASE WHEN d.AccountGroup = 'COGS' THEN a.AmountTRY ELSE 0 END) AS COGSTRY,
    SUM(CASE WHEN d.AccountGroup = 'Revenue' THEN a.AmountTRY ELSE 0 END)
      - SUM(CASE WHEN d.AccountGroup = 'COGS' THEN a.AmountTRY ELSE 0 END) AS GrossProfitTRY,
    SUM(CASE WHEN d.AccountGroup = 'Operating Expense' THEN a.AmountTRY ELSE 0 END) AS OperatingExpenseTRY,
    SUM(CASE WHEN d.AccountGroup = 'Revenue' THEN a.AmountTRY ELSE 0 END)
      - SUM(CASE WHEN d.AccountGroup IN ('COGS', 'Operating Expense') THEN a.AmountTRY ELSE 0 END) AS EBITDATRY
FROM fact_actuals a
JOIN dim_account d ON d.AccountKey = a.AccountKey
GROUP BY a.Month;

CREATE VIEW vw_fy2026_budget_vs_forecast AS
SELECT
    Metric,
    CurrentValueTRY AS ForecastTRY,
    ComparatorValueTRY AS BudgetTRY,
    VarianceTRY,
    VariancePct,
    Status
FROM variance_analysis
WHERE Comparison = 'FY2026 Forecast vs Budget'
ORDER BY MetricOrder;

CREATE VIEW vw_department_ebitda_variance AS
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
    f.ForecastEBITDATRY - b.BudgetEBITDATRY AS VarianceTRY,
    CASE
        WHEN b.BudgetEBITDATRY = 0 THEN NULL
        ELSE (f.ForecastEBITDATRY - b.BudgetEBITDATRY) / ABS(b.BudgetEBITDATRY)
    END AS VariancePct
FROM forecast f
JOIN budget b ON b.Department = f.Department;

CREATE VIEW vw_scenario_decision_summary AS
SELECT
    Scenario,
    RevenueTRY,
    GrossProfitTRY,
    EBITDATRY,
    EBITDAMarginPct,
    EndingCashTRY,
    MinimumCashTRY,
    CashConversionCycleDays
FROM scenario_summary
ORDER BY ScenarioOrder;

CREATE VIEW vw_forecast_model_governance AS
SELECT
    BusinessUnit,
    Model,
    MAE,
    RMSE,
    WAPE,
    Bias,
    ChampionFlag
FROM forecast_model_comparison
ORDER BY BusinessUnit, Score;
