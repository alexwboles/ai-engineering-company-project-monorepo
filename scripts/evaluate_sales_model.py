"""Formally evaluate the HealthCore revenue model without touching test years."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit, learning_curve

from scripts.train_sales_model import DATA_PATH, _features, build_model, load_sales, split_by_year

EVAL_DIR = Path(__file__).resolve().parents[1] / "data" / "eval"
LEARNING_CURVE_PATH = EVAL_DIR / "learning_curve.png"
REPORT_PATH = EVAL_DIR / "evaluation_report.md"
N_SPLITS = 5


def temporal_cv_splits(sample_count: int, n_splits: int = N_SPLITS) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return chronological train/validation folds with no shuffling."""

    splitter = TimeSeriesSplit(n_splits=n_splits)
    indices = np.arange(sample_count)
    return [(train_idx, validation_idx) for train_idx, validation_idx in splitter.split(indices)]


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(actual, predicted)))


def temporal_cross_validation(train: pd.DataFrame, n_splits: int = N_SPLITS) -> dict[str, Any]:
    """Calculate MAE and RMSE for every chronological fold."""

    base_year = int(train["month"].dt.year.min())
    features = _features(train, base_year)
    target = train["revenue_usd"].to_numpy(dtype=float)
    folds: list[dict[str, float | int]] = []
    for fold_number, (train_idx, validation_idx) in enumerate(temporal_cv_splits(len(train), n_splits), start=1):
        model = build_model()
        model.fit(features.iloc[train_idx], target[train_idx])
        train_prediction = model.predict(features.iloc[train_idx])
        validation_prediction = model.predict(features.iloc[validation_idx])
        folds.append(
            {
                "fold": fold_number,
                "train_end_index": int(train_idx[-1]),
                "validation_start_index": int(validation_idx[0]),
                "train_mae": float(mean_absolute_error(target[train_idx], train_prediction)),
                "validation_mae": float(mean_absolute_error(target[validation_idx], validation_prediction)),
                "train_rmse": _rmse(target[train_idx], train_prediction),
                "validation_rmse": _rmse(target[validation_idx], validation_prediction),
            }
        )

    frame = pd.DataFrame(folds)
    return {
        "folds": folds,
        "validation_mae_mean": float(frame["validation_mae"].mean()),
        "validation_mae_std": float(frame["validation_mae"].std(ddof=0)),
        "validation_rmse_mean": float(frame["validation_rmse"].mean()),
        "validation_rmse_std": float(frame["validation_rmse"].std(ddof=0)),
        "train_mae_mean": float(frame["train_mae"].mean()),
        "train_rmse_mean": float(frame["train_rmse"].mean()),
    }


def make_learning_curve(train: pd.DataFrame, n_splits: int = N_SPLITS) -> dict[str, list[float]]:
    """Generate training and validation RMSE as the training set grows."""

    base_year = int(train["month"].dt.year.min())
    features = _features(train, base_year)
    target = train["revenue_usd"].to_numpy(dtype=float)
    sizes, train_scores, validation_scores = learning_curve(
        build_model(),
        features,
        target,
        cv=TimeSeriesSplit(n_splits=n_splits),
        train_sizes=np.linspace(0.3, 1.0, 5),
        scoring="neg_root_mean_squared_error",
        shuffle=False,
        n_jobs=1,
    )
    train_rmse = (-train_scores).mean(axis=1)
    validation_rmse = (-validation_scores).mean(axis=1)
    return {
        "train_sizes": sizes.astype(int).tolist(),
        "train_rmse": train_rmse.astype(float).tolist(),
        "validation_rmse": validation_rmse.astype(float).tolist(),
    }


def diagnose_fit(curve: dict[str, list[float]]) -> tuple[str, str]:
    """Classify fit from the final learning-curve gap and convergence pattern."""

    train_rmse = np.asarray(curve["train_rmse"], dtype=float)
    validation_rmse = np.asarray(curve["validation_rmse"], dtype=float)
    final_train = float(train_rmse[-1])
    final_validation = float(validation_rmse[-1])
    relative_gap = (final_validation - final_train) / final_validation if final_validation else 0.0
    if relative_gap >= 0.25 and final_train < final_validation:
        return (
            "overfitting",
            "Reduce variance by setting `max_depth=8` and `min_samples_leaf=6` on the RandomForestRegressor, then rerun the same temporal cross-validation to verify that the validation gap narrows.",
        )
    if relative_gap <= 0.15 and final_train > 0.75 * final_validation:
        return (
            "well fitted",
            "No corrective model change is required; keep the current hyperparameters, preserve the chronological holdout, and monitor the temporal validation mean plus standard deviation before promotion.",
        )
    return (
        "underfitting",
        "Add prior-year same-month revenue and trailing-three-month revenue features before increasing model complexity, then rerun temporal cross-validation to test whether the high, converged error falls.",
    )


def write_learning_curve(curve: dict[str, list[float]], path: Path = LEARNING_CURVE_PATH) -> None:
    """Save the required training-vs-validation error plot."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, axis = plt.subplots(figsize=(10, 6))
    axis.plot(curve["train_sizes"], curve["train_rmse"], marker="o", label="Training RMSE")
    axis.plot(curve["train_sizes"], curve["validation_rmse"], marker="o", label="Validation RMSE")
    axis.set_title("HealthCore Random Forest learning curve")
    axis.set_xlabel("Training observations")
    axis.set_ylabel("RMSE (USD)")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_evaluation_report(
    cv_results: dict[str, Any],
    curve: dict[str, list[float]],
    diagnosis: str,
    corrective_action: str,
    path: Path = REPORT_PATH,
) -> None:
    """Write the technical evaluation with evidence and business rationale."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fold_lines = [
        f"| {fold['fold']} | {fold['train_mae']:,.2f} | {fold['validation_mae']:,.2f} | {fold['train_rmse']:,.2f} | {fold['validation_rmse']:,.2f} |"
        for fold in cv_results["folds"]
    ]
    curve_lines = [
        f"| {size} | {train_error:,.2f} | {validation_error:,.2f} |"
        for size, train_error, validation_error in zip(
            curve["train_sizes"], curve["train_rmse"], curve["validation_rmse"]
        )
    ]
    path.write_text(
        "\n".join(
            [
                "# HealthCore Regression Model Evaluation",
                "",
                "## Scope and data contract",
                "",
                "This evaluation reuses the Random Forest model, feature builder, and loader from `scripts/train_sales_model.py`. It uses only the first eight years (2016-2023) for temporal cross-validation; the held-out 2024-2025 test years remain untouched.",
                "",
                "HealthCore's domain vocabulary and governance constraints come from `CONTEXT.md` and `CONTEXT_HEALTHCORE.md`. The model target is the aggregate `revenue_usd` value from the `consolidated` rows, with no patient-level data.",
                "",
                "## Metric choice",
                "",
                "MAE is the primary business metric because the HealthCore contexts emphasize reliable operational reporting and do not define a one-sided penalty for overestimating versus underestimating revenue. MAE maps directly to the average dollar error and treats each miss consistently. RMSE is reported alongside it because its stronger penalty for large errors is a useful warning for unusually risky capacity or cash-planning misses.",
                "",
                "## Temporal cross-validation",
                "",
                "`TimeSeriesSplit(n_splits=5)` preserves chronological order and never shuffles. Each validation window occurs after its corresponding training window.",
                "",
                "| Fold | Train MAE | Validation MAE | Train RMSE | Validation RMSE |",
                "|---:|---:|---:|---:|---:|",
                *fold_lines,
                "",
                f"- Validation MAE: **{cv_results['validation_mae_mean']:,.2f} +/- {cv_results['validation_mae_std']:,.2f} USD**.",
                f"- Validation RMSE: **{cv_results['validation_rmse_mean']:,.2f} +/- {cv_results['validation_rmse_std']:,.2f} USD**.",
                f"- Mean training MAE/RMSE: {cv_results['train_mae_mean']:,.2f} / {cv_results['train_rmse_mean']:,.2f} USD.",
                "",
                "## Learning curve evidence",
                "",
                "The saved `data/eval/learning_curve.png` compares training and validation RMSE as the training set grows.",
                "",
                "| Training observations | Training RMSE | Validation RMSE |",
                "|---:|---:|---:|",
                *curve_lines,
                "",
                f"## Diagnosis: {diagnosis}",
                "",
                f"The final learning-curve values are {curve['train_rmse'][-1]:,.2f} USD training RMSE and {curve['validation_rmse'][-1]:,.2f} USD validation RMSE. The cross-validation results above provide the stability check across different historical windows. Taken together, the model is classified as **{diagnosis}** rather than being approved from a single test score.",
                "",
                "## Corrective action",
                "",
                corrective_action,
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run_evaluation(data_path: Path = DATA_PATH, eval_dir: Path = EVAL_DIR) -> dict[str, Any]:
    """Run temporal CV, learning-curve generation, diagnosis, and reporting."""

    train, _test = split_by_year(load_sales(data_path))
    cv_results = temporal_cross_validation(train)
    curve = make_learning_curve(train)
    diagnosis, corrective_action = diagnose_fit(curve)
    write_learning_curve(curve, eval_dir / LEARNING_CURVE_PATH.name)
    write_evaluation_report(cv_results, curve, diagnosis, corrective_action, eval_dir / REPORT_PATH.name)
    return {
        "cv": cv_results,
        "curve": curve,
        "diagnosis": diagnosis,
        "corrective_action": corrective_action,
    }


if __name__ == "__main__":
    evaluation = run_evaluation()
    print(f"Diagnosis: {evaluation['diagnosis']}")
    print(
        "Validation MAE: "
        f"{evaluation['cv']['validation_mae_mean']:.2f} +/- "
        f"{evaluation['cv']['validation_mae_std']:.2f} USD"
    )
    print(
        "Validation RMSE: "
        f"{evaluation['cv']['validation_rmse_mean']:.2f} +/- "
        f"{evaluation['cv']['validation_rmse_std']:.2f} USD"
    )
    print(f"Learning curve: {LEARNING_CURVE_PATH}")
    print(f"Report: {REPORT_PATH}")
