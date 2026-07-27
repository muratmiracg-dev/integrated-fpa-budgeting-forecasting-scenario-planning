from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "Data"
SQL_DIR = PROJECT_ROOT / "SQL"
REPORTS_DIR = PROJECT_ROOT / "Reports"
IMAGES_DIR = PROJECT_ROOT / "Images"

ACTUAL_START = "2023-01-01"
ACTUAL_END = "2026-06-01"
BUDGET_START = "2026-01-01"
BUDGET_END = "2026-12-01"
ROLLING_FORECAST_END = "2027-06-01"
AS_OF_DATE = "2026-06-30"
RANDOM_SEED = 20260726

CURRENCY = "TRY"
VALUE_SCALE = "TRY millions"
COMPANY_NAME = "Asteria Consumer Group"

BUSINESS_UNITS = (
    "Digital Commerce",
    "Retail Stores",
    "Wholesale",
    "Subscription Services",
    "Shared Services",
)

REGIONS = ("Türkiye", "Europe", "MENA", "Global")

SCENARIOS = {
    "Base": {
        "revenue_multiplier": 1.00,
        "cogs_ratio_multiplier": 1.00,
        "opex_multiplier": 1.00,
        "dso_delta": 0,
        "dio_delta": 0,
        "dpo_delta": 0,
    },
    "Upside": {
        "revenue_multiplier": 1.09,
        "cogs_ratio_multiplier": 0.985,
        "opex_multiplier": 1.025,
        "dso_delta": -3,
        "dio_delta": -4,
        "dpo_delta": 2,
    },
    "Downside": {
        "revenue_multiplier": 0.90,
        "cogs_ratio_multiplier": 1.025,
        "opex_multiplier": 0.965,
        "dso_delta": 5,
        "dio_delta": 7,
        "dpo_delta": -2,
    },
    "Stress": {
        "revenue_multiplier": 0.80,
        "cogs_ratio_multiplier": 1.065,
        "opex_multiplier": 0.925,
        "dso_delta": 12,
        "dio_delta": 15,
        "dpo_delta": -5,
    },
}


ACCOUNT_ROWS = (
    ("A4000", "4000", "Digital Commerce Revenue", "Revenue", "Income Statement", "Revenue", "Digital revenue"),
    ("A4010", "4010", "Retail Revenue", "Revenue", "Income Statement", "Revenue", "Retail revenue"),
    ("A4020", "4020", "Wholesale Revenue", "Revenue", "Income Statement", "Revenue", "Wholesale revenue"),
    ("A4030", "4030", "Subscription Revenue", "Revenue", "Income Statement", "Revenue", "Subscription revenue"),
    ("A5000", "5000", "Product & Service Cost", "COGS", "Income Statement", "Expense", "Revenue percentage"),
    ("A5010", "5010", "Payment & Channel Fees", "COGS", "Income Statement", "Expense", "Revenue percentage"),
    ("A5020", "5020", "Variable Fulfillment Cost", "COGS", "Income Statement", "Expense", "Volume and revenue"),
    ("A6000", "6000", "Salaries", "Operating Expense", "Income Statement", "Expense", "Headcount"),
    ("A6010", "6010", "Benefits & Payroll Taxes", "Operating Expense", "Income Statement", "Expense", "Salaries"),
    ("A6100", "6100", "Marketing & Growth", "Operating Expense", "Income Statement", "Expense", "Revenue percentage"),
    ("A6200", "6200", "Logistics & Warehousing", "Operating Expense", "Income Statement", "Expense", "Volume and inflation"),
    ("A6300", "6300", "Technology & Software", "Operating Expense", "Income Statement", "Expense", "Headcount and contracts"),
    ("A6400", "6400", "Facilities & Rent", "Operating Expense", "Income Statement", "Expense", "Locations and inflation"),
    ("A6500", "6500", "Professional Services", "Operating Expense", "Income Statement", "Expense", "Project plan"),
    ("A6600", "6600", "Travel & Other", "Operating Expense", "Income Statement", "Expense", "Headcount"),
    ("A6700", "6700", "Depreciation & Amortization", "Depreciation", "Income Statement", "Expense", "Capex schedule"),
    ("A6800", "6800", "Net Interest Expense", "Interest", "Income Statement", "Expense", "Debt schedule"),
    ("A6900", "6900", "Income Tax", "Tax", "Income Statement", "Expense", "Taxable income"),
)


COST_CENTER_ROWS = (
    ("CC-101", "Türkiye E-Commerce", "Sales", "Digital Commerce", "Türkiye", 6_200_000, 0.135, 0.38, 0.028, 0.030, 18, 78_000),
    ("CC-102", "Europe E-Commerce", "Sales", "Digital Commerce", "Europe", 3_800_000, 0.165, 0.40, 0.032, 0.032, 11, 86_000),
    ("CC-103", "MENA Marketplace", "Sales", "Digital Commerce", "MENA", 2_200_000, 0.190, 0.42, 0.052, 0.035, 7, 82_000),
    ("CC-201", "Flagship Retail", "Sales", "Retail Stores", "Türkiye", 5_100_000, 0.095, 0.46, 0.020, 0.025, 24, 71_000),
    ("CC-202", "Regional Retail", "Sales", "Retail Stores", "Türkiye", 3_450_000, 0.110, 0.47, 0.018, 0.027, 19, 68_000),
    ("CC-301", "Türkiye Wholesale", "Sales", "Wholesale", "Türkiye", 4_300_000, 0.105, 0.57, 0.010, 0.015, 10, 75_000),
    ("CC-302", "Export Wholesale", "Sales", "Wholesale", "Europe", 3_200_000, 0.145, 0.59, 0.012, 0.018, 8, 84_000),
    ("CC-401", "Subscription Growth", "Customer Success", "Subscription Services", "Türkiye", 1_350_000, 0.220, 0.21, 0.025, 0.018, 13, 80_000),
    ("CC-501", "Brand & Performance Marketing", "Marketing", "Shared Services", "Global", 0, 0.000, 0.00, 0.000, 0.000, 15, 81_000),
    ("CC-601", "Fulfillment & Logistics", "Operations", "Shared Services", "Türkiye", 0, 0.000, 0.00, 0.000, 0.000, 26, 69_000),
    ("CC-701", "Technology & Data", "Technology", "Shared Services", "Global", 0, 0.000, 0.00, 0.000, 0.000, 23, 96_000),
    ("CC-801", "People, Finance & Corporate", "Finance & Corporate", "Shared Services", "Global", 0, 0.000, 0.00, 0.000, 0.000, 18, 88_000),
)


REVENUE_ACCOUNT_BY_BU = {
    "Digital Commerce": "A4000",
    "Retail Stores": "A4010",
    "Wholesale": "A4020",
    "Subscription Services": "A4030",
}
