# HealthCore Regression Model Evaluation

## Scope and data contract

This evaluation reuses the Random Forest model, feature builder, and loader from `scripts/train_sales_model.py`. It uses only the first eight years (2016-2023) for temporal cross-validation; the held-out 2024-2025 test years remain untouched.

HealthCore's domain vocabulary and governance constraints come from `CONTEXT.md` and `CONTEXT_HEALTHCORE.md`. The model target is the aggregate `revenue_usd` value from the `consolidated` rows, with no patient-level data.

## Metric choice

MAE is the primary business metric because the HealthCore contexts emphasize reliable operational reporting and do not define a one-sided penalty for overestimating versus underestimating revenue. MAE maps directly to the average dollar error and treats each miss consistently. RMSE is reported alongside it because its stronger penalty for large errors is a useful warning for unusually risky capacity or cash-planning misses.

## Temporal cross-validation

`TimeSeriesSplit(n_splits=5)` preserves chronological order and never shuffles. Each validation window occurs after its corresponding training window.

| Fold | Train MAE | Validation MAE | Train RMSE | Validation RMSE |
|---:|---:|---:|---:|---:|
| 1 | 103,502.02 | 139,616.52 | 124,590.52 | 162,392.17 |
| 2 | 56,536.51 | 225,869.08 | 70,235.19 | 242,525.76 |
| 3 | 49,843.96 | 133,257.04 | 60,028.84 | 158,471.47 |
| 4 | 45,774.65 | 195,021.40 | 56,879.96 | 214,264.61 |
| 5 | 48,906.61 | 212,571.25 | 62,613.80 | 246,445.46 |

- Validation MAE: **181,267.06 +/- 37,942.60 USD**.
- Validation RMSE: **204,819.89 +/- 37,926.01 USD**.
- Mean training MAE/RMSE: 60,912.75 / 74,869.66 USD.

## Learning curve evidence

The saved `data/eval/learning_curve.png` compares training and validation RMSE as the training set grows.

| Training observations | Training RMSE | Validation RMSE |
|---:|---:|---:|
| 4 | 49,897.63 | 559,428.41 |
| 7 | 81,015.79 | 613,995.04 |
| 10 | 157,224.65 | 562,996.67 |
| 13 | 120,723.38 | 474,233.17 |
| 16 | 124,590.52 | 447,260.31 |

## Diagnosis: overfitting

The final learning-curve values are 124,590.52 USD training RMSE and 447,260.31 USD validation RMSE. The cross-validation results above provide the stability check across different historical windows. Taken together, the model is classified as **overfitting** rather than being approved from a single test score.

## Corrective action

Reduce variance by setting `max_depth=8` and `min_samples_leaf=6` on the RandomForestRegressor, then rerun the same temporal cross-validation to verify that the validation gap narrows.
