-- Integrated FP&A Budgeting, Forecasting & Scenario Planning System
-- Reference relational schema for the portfolio data model.

CREATE TABLE dim_calendar (
    Date DATE PRIMARY KEY,
    MonthKey TEXT NOT NULL UNIQUE,
    MonthLabel TEXT NOT NULL,
    MonthName TEXT NOT NULL,
    MonthNo INTEGER NOT NULL,
    Quarter TEXT NOT NULL,
    Year INTEGER NOT NULL,
    FiscalYear TEXT NOT NULL,
    MonthIndex INTEGER NOT NULL,
    IsActual INTEGER NOT NULL,
    IsBudgetYear INTEGER NOT NULL,
    IsRollingForecast INTEGER NOT NULL
);

CREATE TABLE dim_account (
    AccountKey TEXT PRIMARY KEY,
    AccountCode TEXT NOT NULL UNIQUE,
    AccountName TEXT NOT NULL,
    AccountGroup TEXT NOT NULL,
    Statement TEXT NOT NULL,
    NaturalSign TEXT NOT NULL,
    PrimaryDriver TEXT NOT NULL
);

CREATE TABLE dim_cost_center (
    CostCenterID TEXT PRIMARY KEY,
    CostCenterName TEXT NOT NULL,
    Department TEXT NOT NULL,
    BusinessUnit TEXT NOT NULL,
    Region TEXT NOT NULL,
    BudgetOwner TEXT NOT NULL
);

CREATE TABLE dim_scenario (
    Scenario TEXT PRIMARY KEY,
    ScenarioOrder INTEGER NOT NULL,
    Description TEXT NOT NULL
);

CREATE TABLE fact_actuals (
    Month DATE NOT NULL,
    CostCenterID TEXT NOT NULL,
    Department TEXT NOT NULL,
    BusinessUnit TEXT NOT NULL,
    Region TEXT NOT NULL,
    Version TEXT NOT NULL,
    PeriodStatus TEXT NOT NULL,
    SourceSystem TEXT NOT NULL,
    AccountKey TEXT NOT NULL,
    AmountTRY REAL NOT NULL,
    FOREIGN KEY (Month) REFERENCES dim_calendar(Date),
    FOREIGN KEY (CostCenterID) REFERENCES dim_cost_center(CostCenterID),
    FOREIGN KEY (AccountKey) REFERENCES dim_account(AccountKey)
);

CREATE TABLE fact_budget AS SELECT * FROM fact_actuals WHERE 0;
CREATE TABLE fact_forecast AS SELECT * FROM fact_actuals WHERE 0;

CREATE TABLE fact_scenario (
    Month DATE NOT NULL,
    CostCenterID TEXT NOT NULL,
    Department TEXT NOT NULL,
    BusinessUnit TEXT NOT NULL,
    Region TEXT NOT NULL,
    Version TEXT NOT NULL,
    PeriodStatus TEXT NOT NULL,
    SourceSystem TEXT NOT NULL,
    AccountKey TEXT NOT NULL,
    AmountTRY REAL NOT NULL,
    Scenario TEXT NOT NULL,
    FOREIGN KEY (Month) REFERENCES dim_calendar(Date),
    FOREIGN KEY (CostCenterID) REFERENCES dim_cost_center(CostCenterID),
    FOREIGN KEY (AccountKey) REFERENCES dim_account(AccountKey),
    FOREIGN KEY (Scenario) REFERENCES dim_scenario(Scenario)
);

CREATE TABLE fact_working_capital (
    Month DATE NOT NULL,
    Version TEXT NOT NULL,
    DSO REAL NOT NULL,
    DIO REAL NOT NULL,
    DPO REAL NOT NULL,
    CashConversionCycleDays REAL NOT NULL,
    AccountsReceivableTRY REAL NOT NULL,
    InventoryTRY REAL NOT NULL,
    AccountsPayableTRY REAL NOT NULL,
    NetWorkingCapitalTRY REAL NOT NULL,
    ChangeInNWCTRY REAL NOT NULL
);

CREATE TABLE fact_cash_flow (
    Month DATE NOT NULL,
    Version TEXT NOT NULL,
    BeginningCashTRY REAL NOT NULL,
    CashFromOperationsTRY REAL NOT NULL,
    CapitalExpenditureTRY REAL NOT NULL,
    FinancingCashFlowTRY REAL NOT NULL,
    NetCashFlowTRY REAL NOT NULL,
    EndingCashTRY REAL NOT NULL
);

CREATE INDEX idx_actuals_month_account ON fact_actuals (Month, AccountKey);
CREATE INDEX idx_budget_month_account ON fact_budget (Month, AccountKey);
CREATE INDEX idx_forecast_month_account ON fact_forecast (Month, AccountKey);
CREATE INDEX idx_scenario_month_case ON fact_scenario (Month, Scenario);
