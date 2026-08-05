"""Train and evaluate HealthCore's monthly revenue forecast model.

The source is the provided aggregate HealthCore dataset. It contains no
patient-level data. The model deliberately holds out the latest two calendar
years so Finance sees an honest out-of-time evaluation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import normaltest
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "healthcore_sales.csv"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output"
PLOT_PATH = OUTPUT_DIR / "forecast_vs_actual.png"
METRICS_PATH = OUTPUT_DIR / "metrics.md"
SEED = 42
REQUIRED_COLUMNS = {
    "month",
    "revenue_usd",
    "visits_count",
    "avg_revenue_per_visit_usd",
    "region",
}


def load_sales(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load and validate the provided consolidated monthly revenue data."""

    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Sales dataset is missing required columns: {sorted(missing)}")

    frame["month"] = pd.to_datetime(frame["month"], format="%Y-%m-%d", errors="raise")
    frame = frame.loc[frame["region"].eq("consolidated")].copy()
    frame = frame.dropna(subset=sorted(REQUIRED_COLUMNS)).sort_values("month")
    if frame.empty:
        raise ValueError("Sales dataset has no complete consolidated rows.")
    if (frame["revenue_usd"] <= 0).any():
        raise ValueError("All consolidated revenue values must be positive.")

    expected_months = pd.date_range(frame["month"].min(), frame["month"].max(), freq="MS")
    actual_months = pd.DatetimeIndex(frame["month"].drop_duplicates())
    if not expected_months.equals(actual_months):
        raise ValueError("Sales dataset must contain one row for every month without gaps.")
    return frame.reset_index(drop=True)


def split_by_year(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the first eight years from the two most recent years."""

    years = sorted(frame["month"].dt.year.unique().tolist())
    if len(years) != 10:
        raise ValueError(f"Expected exactly 10 calendar years, found {len(years)}.")
    train_years = set(years[:8])
    test_years = set(years[8:])
    train = frame.loc[frame["month"].dt.year.isin(train_years)].copy()
    test = frame.loc[frame["month"].dt.year.isin(test_years)].copy()
    if train.empty or test.empty or max(train_years) >= min(test_years):
        raise ValueError("Chronological 8-year/2-year split could not be created.")
    return train.reset_index(drop=True), test.reset_index(drop=True)


def _features(frame: pd.DataFrame, base_year: int) -> pd.DataFrame:
    """Build calendar features without using the target or future observations."""

    month_number = frame["month"].dt.month
    return pd.DataFrame(
        {
            "year_index": frame["month"].dt.year - base_year,
            "month_sin": np.sin(2 * np.pi * month_number / 12),
            "month_cos": np.cos(2 * np.pi * month_number / 12),
        },
        index=frame.index,
    )


def build_model() -> Pipeline:
    """Return the reproducible, explainable model selected for Finance."""

    # Random Forest is preferred here over XGBoost: the dataset is small and
    # Finance needs a clear bagging-and-averaging explanation before tuning for
    # maximum accuracy. The fixed seed makes the evaluation reproducible.
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=300,
                    min_samples_leaf=2,
                    random_state=SEED,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def population_stability_index(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    """Measure distribution shift between training and held-out test visits."""

    reference_values = np.asarray(reference, dtype=float)
    current_values = np.asarray(current, dtype=float)
    edges = np.unique(np.quantile(reference_values, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        return 0.0
    edges[0] = -np.inf
    edges[-1] = np.inf
    reference_counts = np.histogram(reference_values, bins=edges)[0].astype(float)
    current_counts = np.histogram(current_values, bins=edges)[0].astype(float)
    reference_share = np.maximum(reference_counts / reference_counts.sum(), 1e-6)
    current_share = np.maximum(current_counts / current_counts.sum(), 1e-6)
    return float(np.sum((current_share - reference_share) * np.log(current_share / reference_share)))


def normalized_gini(actual: pd.Series, predicted: np.ndarray) -> float:
    """Return normalized Gini ranking power for a positive regression target."""

    def _gini(values: np.ndarray, order: np.ndarray) -> float:
        ordered = values[order]
        cumulative = np.cumsum(ordered)
        n = len(ordered)
        return float((cumulative.sum() / cumulative[-1] - (n + 1) / 2) / n)

    actual_values = np.asarray(actual, dtype=float)
    prediction_order = np.argsort(predicted)
    actual_order = np.argsort(actual_values)
    ideal = _gini(actual_values, actual_order)
    return 0.0 if ideal == 0 else float(_gini(actual_values, prediction_order) / ideal)


def k2_score(residuals: np.ndarray) -> float:
    """Return D'Agostino's K-squared statistic for model residuals."""

    if len(residuals) < 8:
        raise ValueError("K2 Score requires at least eight residuals.")
    return float(normaltest(residuals).statistic)


def evaluate_model(model: Pipeline, train: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """Evaluate only on the two held-out years and return JSON-like results."""

    base_year = int(train["month"].dt.year.min())
    x_train = _features(train, base_year)
    x_test = _features(test, base_year)
    y_test = test["revenue_usd"].to_numpy(dtype=float)
    predictions = model.predict(x_test)
    forest = model.named_steps["regressor"]
    tree_predictions = np.stack([tree.predict(model.named_steps["scaler"].transform(x_test)) for tree in forest.estimators_])
    variability = tree_predictions.std(axis=0)
    residuals = y_test - predictions
    mean_revenue = float(test["revenue_usd"].mean())
    mse = float(mean_squared_error(y_test, predictions))
    return {
        "MSE": mse,
        "RMSE_pct_of_test_mean_revenue": float(mse**0.5 / mean_revenue * 100),
        "PSI": population_stability_index(train["visits_count"], test["visits_count"]),
        "Gini": normalized_gini(test["revenue_usd"], predictions),
        "K2 Score": k2_score(residuals),
        "months": test["month"].dt.strftime("%Y-%m").tolist(),
        "actual": y_test.tolist(),
        "predicted": predictions.tolist(),
        "variability": variability.tolist(),
        "train_years": sorted(train["month"].dt.year.unique().tolist()),
        "test_years": sorted(test["month"].dt.year.unique().tolist()),
    }


def write_visualization(metrics: dict[str, Any], path: Path = PLOT_PATH) -> None:
    """Write actuals, predictions, and the Random Forest variability band."""

    path.parent.mkdir(parents=True, exist_ok=True)
    dates = pd.to_datetime(metrics["months"])
    predicted = np.asarray(metrics["predicted"])
    variability = np.asarray(metrics["variability"])
    actual = np.asarray(metrics["actual"])
    fig, axis = plt.subplots(figsize=(12, 6))
    axis.plot(dates, actual, marker="o", label="Actual revenue")
    axis.plot(dates, predicted, marker="o", label="Random Forest prediction")
    axis.fill_between(
        dates,
        predicted - variability,
        predicted + variability,
        alpha=0.25,
        label="Tree prediction variability",
    )
    axis.set_title("HealthCore revenue forecast: 2024-2025 held-out test years")
    axis.set_xlabel("Month")
    axis.set_ylabel("Revenue (USD)")
    axis.legend()
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_metrics_report(metrics: dict[str, Any], path: Path = METRICS_PATH) -> None:
    """Write the Finance-readable test-set metric report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# HealthCore Sales Forecast Metrics",
                "",
                "- Model: Random Forest Regressor with `random_state=42`.",
                f"- Training years: {metrics['train_years'][0]}-{metrics['train_years'][-1]} (first 8 years).",
                f"- Test years: {metrics['test_years'][0]}-{metrics['test_years'][-1]} (most recent 2 years).",
                "- Target: `revenue_usd` from the `consolidated` rows.",
                "- Domain vocabulary and data-governance constraints: repository `CONTEXT.md` and `CONTEXT_HEALTHCORE.md`.",
                "- Dataset provenance: the provided HealthCore aggregate sales file; no values were generated or simulated.",
                "",
                "## Test-set results",
                "",
                f"- **MSE:** {metrics['MSE']:,.2f} USD^2; RMSE is {metrics['RMSE_pct_of_test_mean_revenue']:.2f}% of mean test revenue.",
                f"- **PSI:** {metrics['PSI']:.4f}, measuring train/test shift in `visits_count`.",
                f"- **Gini:** {metrics['Gini']:.4f}, measuring how well predictions rank higher- and lower-revenue months.",
                f"- **K2 Score:** {metrics['K2 Score']:.4f}, D'Agostino K-squared statistic for residual normality.",
                "",
                "MSE explains average squared error in Finance's units, but it cannot show whether the model generalized to unseen years. PSI flags distribution drift, Gini checks ranking quality, and K2 checks whether residuals are unusually skewed or heavy-tailed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run_experiment(data_path: Path = DATA_PATH, output_dir: Path = OUTPUT_DIR) -> dict[str, Any]:
    """Run the complete load, split, train, evaluate, and report workflow."""

    train, test = split_by_year(load_sales(data_path))
    model = build_model()
    base_year = int(train["month"].dt.year.min())
    model.fit(_features(train, base_year), train["revenue_usd"])
    metrics = evaluate_model(model, train, test)
    write_visualization(metrics, output_dir / PLOT_PATH.name)
    write_metrics_report(metrics, output_dir / METRICS_PATH.name)
    return metrics


if __name__ == "__main__":
    result = run_experiment()
    print(f"Training years: {result['train_years']}")
    print(f"Test years: {result['test_years']}")
    for metric in ("MSE", "PSI", "Gini", "K2 Score"):
        print(f"{metric}: {result[metric]:.6f}")
    print(f"Visualization: {PLOT_PATH}")
