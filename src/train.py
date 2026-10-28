"""Training pipeline: baseline and improved Random Forest, XGBoost and their soft-voting mix.

Usage:
    python -m src.train --dataset cicids2017|unsw_nb15 [--n-iter 8] [--tune-sample 60000]

For each algorithm a literature-style baseline (default hyperparameters, threshold 0.5)
and an improved version (correlation filter, 5-fold CV hyperparameter search) are trained
on the same train partition. Three operating points are evaluated for every model, with
thresholds chosen on the validation split: default 0.5, minimum FPR at Recall >= 0.95, and
maximum Recall at FPR <= 0.02.
The best model is chosen on the validation split only; the test split is used once to
report the final numbers.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold

from src import config
from src.data_loader import DataSplits, load_processed, make_splits, stratified_subsample
from src.features import split_column_types
from src.metrics import compute_metrics, select_threshold, select_threshold_for_fpr
from src.models import (
    ALGORITHM_LABELS,
    Algorithm,
    SoftVotingEnsemble,
    attack_scores,
    build_pipeline,
    search_space,
)

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 0.5
TOP_IMPORTANCES = 20
OPERATING_POINTS = ("default", "recall_target", "fpr_budget")


@dataclass
class TrainedModel:
    """A fitted model with the bookkeeping needed for the report."""

    name: str
    algorithm: str
    variant: str
    model: Any
    fit_seconds: float = 0.0
    best_params: dict[str, Any] = field(default_factory=dict)
    cv_average_precision: float | None = None


def tune_hyperparameters(
    algorithm: Algorithm,
    X: pd.DataFrame,
    y: pd.Series,
    numeric: list[str],
    categorical: list[str],
    n_iter: int,
    cv_folds: int,
) -> tuple[dict[str, Any], float]:
    """Randomised search with stratified k-fold CV; every fold refits the whole pipeline."""
    search = RandomizedSearchCV(
        build_pipeline(algorithm, numeric, categorical, improved=True),
        search_space(algorithm),
        n_iter=n_iter,
        cv=StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=config.RANDOM_STATE),
        scoring="average_precision",
        random_state=config.RANDOM_STATE,
        n_jobs=1,
        refit=False,
    )
    search.fit(X, y)
    return dict(search.best_params_), float(search.best_score_)


def train_algorithm(
    algorithm: Algorithm,
    splits: DataSplits,
    n_iter: int,
    tune_sample: int,
    cv_folds: int,
) -> tuple[TrainedModel, TrainedModel]:
    """Train the baseline and the improved version of one algorithm."""
    numeric, categorical = split_column_types(splits.train.X)
    X, y = splits.train.X, splits.train.y

    started = time.perf_counter()
    baseline = build_pipeline(algorithm, numeric, categorical, improved=False).fit(X, y)
    baseline_trained = TrainedModel(
        f"{algorithm}_baseline", algorithm, "baseline", baseline, time.perf_counter() - started
    )
    logger.info("%s baseline fitted in %.0fs", algorithm, baseline_trained.fit_seconds)

    started = time.perf_counter()
    X_sub, y_sub = stratified_subsample(X, y, tune_sample, stratify=splits.train.attack)
    best_params, cv_score = tune_hyperparameters(
        algorithm, X_sub, y_sub, numeric, categorical, n_iter, cv_folds
    )
    logger.info("%s best params %s (CV AP %.4f)", algorithm, best_params, cv_score)
    improved = build_pipeline(algorithm, numeric, categorical, improved=True)
    improved.set_params(**best_params).fit(X, y)
    improved_trained = TrainedModel(
        f"{algorithm}_improved",
        algorithm,
        "improved",
        improved,
        time.perf_counter() - started,
        best_params,
        cv_score,
    )
    logger.info("%s improved fitted in %.0fs", algorithm, improved_trained.fit_seconds)
    return baseline_trained, improved_trained


def build_mix(trained: dict[str, TrainedModel], variant: str) -> TrainedModel:
    """Soft-voting ensemble of the RF and XGBoost models of one variant."""
    members = [trained[f"rf_{variant}"].model, trained[f"xgb_{variant}"].model]
    return TrainedModel(f"mix_{variant}", "mix", variant, SoftVotingEnsemble(members))


def choose_thresholds(
    y_val: np.ndarray, val_scores: np.ndarray, recall_target: float, fpr_budget: float
) -> dict[str, float]:
    """Decision thresholds of the three operating points, all chosen on validation data.

    - default: fixed 0.5, as most published baselines.
    - recall_target: minimum FPR with Recall >= target (the AGENT.md criterion).
    - fpr_budget: maximum Recall with FPR <= budget (a fixed false alarm allowance).
    """
    return {
        "default": DEFAULT_THRESHOLD,
        "recall_target": select_threshold(y_val, val_scores, recall_target),
        "fpr_budget": select_threshold_for_fpr(y_val, val_scores, fpr_budget),
    }


def metric_rows(
    name: str,
    y_val: np.ndarray,
    y_test: np.ndarray,
    val_scores: np.ndarray,
    test_scores: np.ndarray,
    thresholds: dict[str, float],
) -> list[dict[str, Any]]:
    """Long-format metric rows (model x operating point x split) for one model."""
    algorithm, variant = name.split("_")
    rows: list[dict[str, Any]] = []
    for operating_point in OPERATING_POINTS:
        for split_name, y, split_scores in (("val", y_val, val_scores), ("test", y_test, test_scores)):
            metrics = compute_metrics(y, split_scores, thresholds[operating_point])
            rows.append(
                {
                    "model": name,
                    "algorithm": algorithm,
                    "variant": variant,
                    "operating_point": operating_point,
                    "split": split_name,
                    **metrics.to_dict(),
                }
            )
    return rows


def evaluate_models(
    models: list[TrainedModel], splits: DataSplits, recall_target: float, fpr_budget: float
) -> tuple[list[dict[str, Any]], dict[str, np.ndarray], dict[str, dict[str, float]]]:
    """Score every model on val and test and compute metrics at the three operating points.

    Returns (metric rows in long format, score arrays, thresholds per model). Thresholds
    are always chosen on the validation split.
    """
    rows: list[dict[str, Any]] = []
    scores: dict[str, np.ndarray] = {}
    thresholds: dict[str, dict[str, float]] = {}
    y_val, y_test = splits.val.y.to_numpy(), splits.test.y.to_numpy()
    for trained in models:
        val_scores = attack_scores(trained.model, splits.val.X)
        test_scores = attack_scores(trained.model, splits.test.X)
        scores[f"{trained.name}_val"] = val_scores
        scores[f"{trained.name}_test"] = test_scores
        thresholds[trained.name] = choose_thresholds(y_val, val_scores, recall_target, fpr_budget)
        rows += metric_rows(trained.name, y_val, y_test, val_scores, test_scores, thresholds[trained.name])
    return rows, scores, thresholds


def select_best(rows: list[dict[str, Any]], recall_target: float) -> str:
    """Name of the model with the lowest validation FPR at the recall-target operating point.

    Only models whose validation recall meets the target are eligible; ties are broken by
    validation F1. If no model reaches the target, the one with the highest recall wins.
    """
    candidates = [r for r in rows if r["operating_point"] == "recall_target" and r["split"] == "val"]
    eligible = [r for r in candidates if r["recall"] >= recall_target]
    if not eligible:
        return max(candidates, key=lambda r: (r["recall"], -r["fpr"]))["model"]
    return min(eligible, key=lambda r: (r["fpr"], -r["f1"]))["model"]


def select_best_for_budget(rows: list[dict[str, Any]]) -> str:
    """Name of the model with the highest validation recall at the FPR-budget operating point."""
    candidates = [r for r in rows if r["operating_point"] == "fpr_budget" and r["split"] == "val"]
    return max(candidates, key=lambda r: (r["recall"], -r["fpr"]))["model"]


def feature_importances(trained: TrainedModel) -> dict[str, float]:
    """Top feature importances of a fitted RF/XGBoost pipeline, keyed by feature name."""
    pipeline = trained.model
    names = pipeline[:-1].get_feature_names_out()
    values = np.asarray(pipeline[-1].feature_importances_, dtype=float)
    order = np.argsort(-values)[:TOP_IMPORTANCES]
    return {str(names[i]): float(values[i]) for i in order}


def run(
    dataset_key: str,
    n_iter: int = 8,
    tune_sample: int = 60_000,
    cv_folds: int = 5,
) -> str:
    """Train, evaluate and persist everything for one dataset; returns the best model name."""
    dataset = config.get_dataset(dataset_key)
    df = load_processed(dataset_key)
    splits = make_splits(df)
    logger.info(
        "%s: train %d, val %d, test %d",
        dataset.display_name,
        len(splits.train),
        len(splits.val),
        len(splits.test),
    )

    trained: dict[str, TrainedModel] = {}
    for algorithm in ("rf", "xgb"):
        for model in train_algorithm(algorithm, splits, n_iter, tune_sample, cv_folds):  # type: ignore[arg-type]
            trained[model.name] = model
    for variant in ("baseline", "improved"):
        mix = build_mix(trained, variant)
        trained[mix.name] = mix

    models = list(trained.values())
    rows, scores, thresholds = evaluate_models(
        models, splits, config.RECALL_TARGET, config.FPR_TARGET
    )
    best_name = select_best(rows, config.RECALL_TARGET)
    best_budget_name = select_best_for_budget(rows)
    logger.info("Best model on validation: %s (best at FPR budget: %s)", best_name, best_budget_name)

    dataset.models_dir.mkdir(parents=True, exist_ok=True)
    dataset.reports_dir.mkdir(parents=True, exist_ok=True)

    metrics_frame = pd.DataFrame(rows)
    metrics_frame.insert(0, "dataset", dataset.key)
    metrics_frame.to_csv(dataset.reports_dir / "metrics.csv", index=False)

    np.savez_compressed(
        dataset.models_dir / "scores.npz",
        **scores,
        y_val=splits.val.y.to_numpy(),
        y_test=splits.test.y.to_numpy(),
        attack_val=splits.val.attack.to_numpy().astype(str),
        attack_test=splits.test.attack.to_numpy().astype(str),
    )

    ensemble_note = "ensemble of the Random Forest and XGBoost members of the same variant"
    summary = {
        "dataset": dataset.key,
        "random_state": config.RANDOM_STATE,
        "split_sizes": {"train": len(splits.train), "val": len(splits.val), "test": len(splits.test)},
        "recall_target": config.RECALL_TARGET,
        "fpr_target": config.FPR_TARGET,
        "best_model": best_name,
        "best_model_fpr_budget": best_budget_name,
        "thresholds": thresholds,
        "n_iter": n_iter,
        "tune_sample": tune_sample,
        "cv_folds": cv_folds,
        "models": {
            t.name: {
                "label": f"{ALGORITHM_LABELS[t.algorithm]} ({t.variant})",
                "fit_seconds": round(t.fit_seconds, 1),
                "best_params": {k: (v if v is None or isinstance(v, (int, float, str)) else str(v)) for k, v in t.best_params.items()},
                "cv_average_precision": t.cv_average_precision,
                "note": ensemble_note if t.algorithm == "mix" else "",
            }
            for t in models
        },
        "feature_importances": {
            name: feature_importances(trained[name]) for name in ("rf_improved", "xgb_improved")
        },
        "features_dropped_by_filter": {
            name: [
                str(f)
                for f in np.setdiff1d(
                    trained[name].model[:-2].get_feature_names_out(),
                    trained[name].model[:-1].get_feature_names_out(),
                )
            ]
            for name in ("rf_improved", "xgb_improved")
        },
    }
    (dataset.reports_dir / "training_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    best = trained[best_name]
    joblib.dump(
        {
            "dataset": dataset.key,
            "model_name": best_name,
            "model": best.model,
            "thresholds": thresholds[best_name],
            "threshold": thresholds[best_name]["recall_target"],
            "feature_columns": splits.feature_names,
            "numeric_columns": split_column_types(splits.train.X)[0],
            "categorical_columns": split_column_types(splits.train.X)[1],
        },
        dataset.models_dir / "best_model.joblib",
        compress=3,
    )
    return best_name


def rescore(dataset_key: str) -> str:
    """Recompute thresholds, metrics and the best model from the saved validation/test scores.

    Useful when only the decision criteria change: no model is retrained. The saved best
    model bundle is updated in place and must still belong to the selected best model.
    """
    dataset = config.get_dataset(dataset_key)
    summary_path = dataset.reports_dir / "training_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    saved = np.load(dataset.models_dir / "scores.npz")
    y_val, y_test = saved["y_val"], saved["y_test"]

    rows: list[dict[str, Any]] = []
    thresholds: dict[str, dict[str, float]] = {}
    for name in summary["models"]:
        thresholds[name] = choose_thresholds(
            y_val, saved[f"{name}_val"], config.RECALL_TARGET, config.FPR_TARGET
        )
        rows += metric_rows(name, y_val, y_test, saved[f"{name}_val"], saved[f"{name}_test"], thresholds[name])
    best = select_best(rows, config.RECALL_TARGET)

    bundle_path = dataset.models_dir / "best_model.joblib"
    bundle = joblib.load(bundle_path)
    if bundle["model_name"] != best:
        raise RuntimeError(
            f"Saved model is {bundle['model_name']} but the criteria now select {best}; retrain."
        )
    bundle["thresholds"] = thresholds[best]
    bundle["threshold"] = thresholds[best]["recall_target"]
    joblib.dump(bundle, bundle_path, compress=3)

    metrics_frame = pd.DataFrame(rows)
    metrics_frame.insert(0, "dataset", dataset.key)
    metrics_frame.to_csv(dataset.reports_dir / "metrics.csv", index=False)
    summary.pop("calibrated_thresholds", None)
    summary.update(
        thresholds=thresholds,
        best_model=best,
        best_model_fpr_budget=select_best_for_budget(rows),
        recall_target=config.RECALL_TARGET,
        fpr_target=config.FPR_TARGET,
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return best


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train the IDS models.")
    parser.add_argument("--dataset", choices=list(config.DATASETS), required=True)
    parser.add_argument("--n-iter", type=int, default=8, help="random search candidates")
    parser.add_argument("--tune-sample", type=int, default=60_000, help="rows used for the search")
    parser.add_argument("--cv-folds", type=int, default=5)
    parser.add_argument(
        "--rescore", action="store_true", help="recompute metrics and thresholds from saved scores"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    if args.rescore:
        logger.info("Best model: %s", rescore(args.dataset))
        return 0
    run(args.dataset, args.n_iter, args.tune_sample, args.cv_folds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
