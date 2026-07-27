from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .config import ACTUAL_END, DATA_DIR, RANDOM_SEED, ROLLING_FORECAST_END

MODEL_NAMES = (
    "Seasonal Naive",
    "Linear Trend + Seasonality",
    "Log-Ridge Seasonal",
    "Gradient Boosting",
)


def _feature_matrix(
    dates: pd.Series | pd.DatetimeIndex,
    origin: pd.Timestamp,
    quadratic: bool = False,
) -> np.ndarray:
    idx = pd.DatetimeIndex(pd.to_datetime(dates))
    t = np.array(
        [(date.year - origin.year) * 12 + date.month - origin.month for date in idx],
        dtype=float,
    )
    month = idx.month.to_numpy()
    columns = [
        t,
        np.sin(2 * np.pi * month / 12),
        np.cos(2 * np.pi * month / 12),
        np.sin(4 * np.pi * month / 12),
        np.cos(4 * np.pi * month / 12),
    ]
    if quadratic:
        columns.append((t**2) / 100.0)
    for month_no in range(2, 13):
        columns.append((month == month_no).astype(float))
    return np.column_stack(columns)


def _seasonal_naive(
    train_dates: pd.Series,
    train_values: np.ndarray,
    predict_dates: pd.Series | pd.DatetimeIndex,
) -> np.ndarray:
    lookup = {
        pd.Timestamp(date).to_period("M"): float(value)
        for date, value in zip(train_dates, train_values, strict=True)
    }
    values = []
    fallback = float(np.mean(train_values[-6:]))
    for date in pd.to_datetime(predict_dates):
        period = pd.Timestamp(date).to_period("M")
        value = lookup.get(period - 12, fallback)
        values.append(max(value, 0))
        lookup[period] = max(value, 0)
    return np.array(values)


def _fit_predict(
    model_name: str,
    train_dates: pd.Series,
    train_values: np.ndarray,
    predict_dates: pd.Series | pd.DatetimeIndex,
) -> np.ndarray:
    origin = pd.Timestamp(train_dates.min())
    if model_name == "Seasonal Naive":
        return _seasonal_naive(train_dates, train_values, predict_dates)
    if model_name == "Linear Trend + Seasonality":
        model = LinearRegression()
        model.fit(_feature_matrix(train_dates, origin), train_values)
        return np.maximum(model.predict(_feature_matrix(predict_dates, origin)), 0)
    if model_name == "Log-Ridge Seasonal":
        model = Ridge(alpha=3.0)
        model.fit(
            _feature_matrix(train_dates, origin, quadratic=True),
            np.log1p(train_values),
        )
        return np.maximum(
            np.expm1(model.predict(_feature_matrix(predict_dates, origin, quadratic=True))),
            0,
        )
    if model_name == "Gradient Boosting":
        model = HistGradientBoostingRegressor(
            learning_rate=0.07,
            max_iter=180,
            max_leaf_nodes=10,
            l2_regularization=0.7,
            random_state=RANDOM_SEED,
        )
        model.fit(_feature_matrix(train_dates, origin, quadratic=True), train_values)
        return np.maximum(
            model.predict(_feature_matrix(predict_dates, origin, quadratic=True)),
            0,
        )
    raise ValueError(f"Unknown model: {model_name}")


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = predicted - actual
    denominator = max(float(np.abs(actual).sum()), 1.0)
    wape = float(np.abs(errors).sum() / denominator)
    bias = float(errors.sum() / denominator)
    return {
        "MAE": float(mean_absolute_error(actual, predicted)),
        "RMSE": float(math.sqrt(mean_squared_error(actual, predicted))),
        "WAPE": wape,
        "Bias": bias,
        "Score": wape + 0.30 * abs(bias),
    }


def _load_monthly_revenue() -> pd.DataFrame:
    actuals = pd.read_csv(DATA_DIR / "fact_actuals.csv", parse_dates=["Month"])
    accounts = pd.read_csv(DATA_DIR / "dim_account.csv")
    revenue_accounts = accounts.loc[
        accounts["AccountGroup"] == "Revenue", "AccountKey"
    ].tolist()
    return (
        actuals[actuals["AccountKey"].isin(revenue_accounts)]
        .groupby(["Month", "BusinessUnit"], as_index=False)["AmountTRY"]
        .sum()
        .rename(columns={"AmountTRY": "RevenueTRY"})
        .sort_values(["BusinessUnit", "Month"])
    )


def run_forecasting() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    revenue = _load_monthly_revenue()
    comparison_rows: list[dict] = []
    backtest_rows: list[dict] = []
    forecast_rows: list[dict] = []
    forecast_months = pd.date_range(
        pd.Timestamp(ACTUAL_END) + pd.DateOffset(months=1),
        pd.Timestamp(ROLLING_FORECAST_END),
        freq="MS",
    )

    for business_unit, frame in revenue.groupby("BusinessUnit"):
        frame = frame.sort_values("Month").reset_index(drop=True)
        train = frame[frame["Month"] <= pd.Timestamp("2025-12-01")]
        test = frame[frame["Month"] > pd.Timestamp("2025-12-01")]
        model_predictions: dict[str, np.ndarray] = {}
        for model_name in MODEL_NAMES:
            predicted = _fit_predict(
                model_name,
                train["Month"],
                train["RevenueTRY"].to_numpy(dtype=float),
                test["Month"],
            )
            model_predictions[model_name] = predicted
            metrics = _metrics(test["RevenueTRY"].to_numpy(dtype=float), predicted)
            comparison_rows.append(
                {
                    "BusinessUnit": business_unit,
                    "Model": model_name,
                    **{key: round(value, 6) for key, value in metrics.items()},
                }
            )
            for month, actual_value, predicted_value in zip(
                test["Month"],
                test["RevenueTRY"],
                predicted,
                strict=True,
            ):
                backtest_rows.append(
                    {
                        "Month": month,
                        "BusinessUnit": business_unit,
                        "Model": model_name,
                        "ActualRevenueTRY": round(float(actual_value), 2),
                        "PredictedRevenueTRY": round(float(predicted_value), 2),
                        "AbsoluteErrorTRY": round(abs(float(predicted_value - actual_value)), 2),
                        "AbsolutePercentageError": round(
                            abs(float(predicted_value - actual_value))
                            / max(float(actual_value), 1),
                            6,
                        ),
                    }
                )

        unit_metrics = [
            row for row in comparison_rows if row["BusinessUnit"] == business_unit
        ]
        champion = min(unit_metrics, key=lambda row: row["Score"])["Model"]
        for row in unit_metrics:
            row["ChampionFlag"] = row["Model"] == champion

        full_dates = frame["Month"]
        full_values = frame["RevenueTRY"].to_numpy(dtype=float)
        future = _fit_predict(champion, full_dates, full_values, forecast_months)
        test_pred = model_predictions[champion]
        residual_std = float(
            np.std(test["RevenueTRY"].to_numpy(dtype=float) - test_pred, ddof=1)
        )
        for month, forecast_value in zip(forecast_months, future, strict=True):
            interval = 1.28 * residual_std * math.sqrt(
                1 + max((month.year - 2026) * 12 + month.month - 6, 0) / 24
            )
            forecast_rows.append(
                {
                    "Month": month,
                    "BusinessUnit": business_unit,
                    "ChampionModel": champion,
                    "ForecastRevenueTRY": round(float(forecast_value), 2),
                    "Lower80RevenueTRY": round(max(float(forecast_value - interval), 0), 2),
                    "Upper80RevenueTRY": round(float(forecast_value + interval), 2),
                    "ResidualStdTRY": round(residual_std, 2),
                    "ForecastHorizonMonth": (
                        (month.year - 2026) * 12 + month.month - 6
                    ),
                }
            )

    comparison = pd.DataFrame(comparison_rows).sort_values(
        ["BusinessUnit", "Score"]
    )
    backtest = pd.DataFrame(backtest_rows)
    forecast = pd.DataFrame(forecast_rows).sort_values(
        ["Month", "BusinessUnit"]
    )
    comparison.to_csv(DATA_DIR / "forecast_model_comparison.csv", index=False)
    backtest.to_csv(
        DATA_DIR / "forecast_backtest.csv", index=False, date_format="%Y-%m-%d"
    )
    forecast.to_csv(
        DATA_DIR / "revenue_forecast.csv", index=False, date_format="%Y-%m-%d"
    )
    return forecast, comparison, backtest


if __name__ == "__main__":
    forecast, comparison, backtest = run_forecasting()
    print(f"revenue_forecast: {len(forecast):,} rows")
    print(f"forecast_model_comparison: {len(comparison):,} rows")
    print(f"forecast_backtest: {len(backtest):,} rows")
    print(
        comparison.loc[comparison["ChampionFlag"], ["BusinessUnit", "Model", "WAPE"]]
        .to_string(index=False)
    )
