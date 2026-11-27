import pandas as pd
import pytest
from fpa_system.config import ACTUAL_END, DATA_DIR


def test_scenario_tax_is_accrued_on_year_to_date_ebt() -> None:
    """Tax follows the fiscal year: YTD tax equals 25% of positive YTD EBT in every forecast month.

    Taxing each month's positive EBT on its own ignored loss months, so the Stress scenario paid
    tax across a loss-making forecast window.
    """
    pnl = pd.read_csv(DATA_DIR / "scenario_monthly_pnl.csv", parse_dates=["Month"])
    pnl = pnl.sort_values(["Scenario", "Month"])
    pnl["Year"] = pnl["Month"].dt.year
    grouped = pnl.groupby(["Scenario", "Year"])
    pnl["YtdEBT"] = grouped["EBTTRY"].cumsum()
    pnl["YtdTax"] = grouped["TaxTRY"].cumsum()
    forecast = pnl[pnl["Month"] > pd.Timestamp(ACTUAL_END)]
    expected = 0.25 * forecast["YtdEBT"].clip(lower=0)
    # Each month is rounded to cents, so allow a few cents of accumulated rounding.
    assert forecast["YtdTax"].to_numpy() == pytest.approx(expected.to_numpy(), abs=0.5)
    stress_2027 = forecast[(forecast["Scenario"] == "Stress") & (forecast["Year"] == 2027)]
    assert stress_2027["TaxTRY"].sum() == pytest.approx(
        0.25 * max(stress_2027["EBTTRY"].sum(), 0.0), abs=0.5
    )
