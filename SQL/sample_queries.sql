-- 1. FY2026 rolling forecast versus budget.
SELECT *
FROM vw_fy2026_budget_vs_forecast;

-- 2. Departments with the largest unfavorable EBITDA variance.
SELECT
    Department,
    ForecastEBITDATRY,
    BudgetEBITDATRY,
    VarianceTRY,
    VariancePct
FROM vw_department_ebitda_variance
ORDER BY VarianceTRY ASC;

-- 3. Scenario resilience and minimum-liquidity comparison.
SELECT
    Scenario,
    RevenueTRY,
    EBITDATRY,
    EBITDAMarginPct,
    EndingCashTRY,
    MinimumCashTRY,
    CashConversionCycleDays
FROM vw_scenario_decision_summary;

-- 4. Twelve-month actual revenue and EBITDA trend.
SELECT
    Month,
    RevenueTRY,
    GrossProfitTRY,
    EBITDATRY,
    CASE WHEN RevenueTRY = 0 THEN NULL ELSE EBITDATRY / RevenueTRY END AS EBITDAMarginPct
FROM vw_monthly_actual_pnl
ORDER BY Month DESC
LIMIT 12;

-- 5. Cost-center budget workflow.
SELECT
    Department,
    CostCenterName,
    BudgetOwner,
    Status,
    ReviewRounds,
    julianday(ApprovalDate) - julianday(SubmittedDate) AS ApprovalCycleDays
FROM budget_submissions
ORDER BY Department, CostCenterName;

-- 6. Champion forecast model by business unit.
SELECT
    BusinessUnit,
    Model,
    WAPE,
    Bias
FROM vw_forecast_model_governance
WHERE CAST(ChampionFlag AS TEXT) IN ('True', 'true', '1');

-- 7. Working-capital gap to budget at year end.
SELECT
    f.DSO - b.DSO AS DSOGapDays,
    f.DIO - b.DIO AS DIOGapDays,
    f.DPO - b.DPO AS DPOGapDays,
    f.CashConversionCycleDays - b.CashConversionCycleDays AS CCCGapDays,
    f.NetWorkingCapitalTRY - b.NetWorkingCapitalTRY AS NWCVarianceTRY
FROM fact_working_capital f
JOIN fact_working_capital b ON b.Month = f.Month
WHERE f.Version = 'Forecast'
  AND b.Version = 'Budget'
  AND f.Month = '2026-12-01';
