# HealthCore Sales Forecast Metrics

- Model: Random Forest Regressor with `random_state=42`.
- Training years: 2016-2023 (first 8 years).
- Test years: 2024-2025 (most recent 2 years).
- Target: `revenue_usd` from the `consolidated` rows.
- Domain vocabulary and data-governance constraints: repository `CONTEXT.md` and `CONTEXT_HEALTHCORE.md`.
- Dataset provenance: the provided HealthCore aggregate sales file; no values were generated or simulated.

## Test-set results

- **MSE:** 76,682,751,968.75 USD^2; RMSE is 8.23% of mean test revenue.
- **PSI:** 6.5966, measuring train/test shift in `visits_count`.
- **Gini:** 0.8847, measuring how well predictions rank higher- and lower-revenue months.
- **K2 Score:** 0.2639, D'Agostino K-squared statistic for residual normality.

MSE explains average squared error in Finance's units, but it cannot show whether the model generalized to unseen years. PSI flags distribution drift, Gini checks ranking quality, and K2 checks whether residuals are unusually skewed or heavy-tailed.
