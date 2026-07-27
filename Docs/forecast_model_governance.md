# Forecast Model Governance

## Objective

The forecasting layer supports planning decisions; it does not replace management judgment. Each model must be measurable, explainable, reproducible, and monitored after selection.

## Candidate models

1. Seasonal Naive: prior comparable seasonal value.
2. Linear Trend + Seasonality: interpretable trend and seasonal components.
3. Log-Ridge Seasonal: regularized log-scale model for stable proportional effects.
4. Gradient Boosting: nonlinear benchmark using engineered time features.

## Evaluation

Models are compared on:

- MAE: absolute error in TRY
- RMSE: greater penalty for large misses
- WAPE: scale-independent absolute error
- Bias: systematic under- or over-forecasting
- Combined score: balances error and bias

The champion is the lowest governed score for the business unit. Exactly one champion must exist per business unit.

## Current champions

| Business unit | Model | WAPE | Bias |
|---|---|---:|---:|
| Digital Commerce | Linear Trend + Seasonality | 1.0% | -0.8% |
| Retail Stores | Linear Trend + Seasonality | 2.8% | +2.8% |
| Subscription Services | Log-Ridge Seasonal | 3.6% | +1.5% |
| Wholesale | Log-Ridge Seasonal | 1.7% | -0.4% |

## Monitoring

- Recalculate error after each monthly close.
- Review WAPE and bias by business unit.
- Challenge material overrides and document the rationale.
- Retrain only after the closed period is loaded.
- Retain the incumbent model unless a challenger wins consistently.
- Escalate structural breaks such as channel changes, price regime shifts, or abnormal promotions.

## Limitations

The portfolio dataset is synthetic. Model performance illustrates governance and implementation patterns; it is not evidence of expected performance on a real company’s data.
