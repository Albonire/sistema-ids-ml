"""Formal experiments for the final deliverable.

Usage:
    python -m src.experiments --dataset unsw_nb15|cicids2017 --task seeds|pairwise|official|features|all

Tasks (outputs go to `reports/<dataset>/`):

- seeds: repeat the whole split-and-fit protocol with several seeds and summarise the spread
  (`multiseed.csv`, `multiseed_summary.csv`, `multiseed_summary.json`). The hyperparameters
  found by the seed 42 search are reused for the other seeds, so the search itself is not
  repeated; the tuning rows of seed 42 overlap the test rows of other seeds.
- pairwise: paired bootstrap tests between models on the saved test scores (`pairwise_tests.csv`).
- official: UNSW-NB15 only. Train on the official training partition and test on the official
  testing partition, with and without cleaning, plus 5-fold CV on the training partition
  (`official_partitions.csv`).
- features: refit the improved XGBoost without groups of suspected shortcut variables
  (`feature_ablation.csv`).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from src import config
from src.data_loader import load_processed, make_splits, split_features_target
from src.features import split_column_types
from src.metrics import compute_metrics, paired_bootstrap_difference
from src.models import attack_scores, build_pipeline
from src.preprocess import clean, normalize_unsw
from src.train import (
    OPERATING_POINTS,
    TrainedModel,
    build_mix,
    choose_thresholds,
    evaluate_models,
    metric_rows,
    select_best,
    select_best_for_budget,
)

logger = logging.getLogger(__name__)

SEEDS: tuple[int, ...] = (42, 1, 2, 3, 4)
SUMMARY_METRICS = ("recall", "fpr", "precision", "f1", "accuracy", "roc_auc", "pr_auc", "fp", "fn")

PAIRS: tuple[tuple[str, str], ...] = (
    ("rf_improved", "rf_baseline"),
    ("xgb_improved", "xgb_baseline"),
    ("mix_improved", "mix_baseline"),
    ("xgb_improved", "rf_improved"),
    ("xgb_baseline", "rf_baseline"),
    ("mix_improved", "xgb_improved"),
    ("mix_baseline", "xgb_baseline"),
)

ENGELEN_SHORTCUTS: tuple[str, ...] = (
    "Fwd Header Length",
    "Total Fwd Packets",
    "min_seg_size_forward",
    "Init_Win_bytes_forward",
    "SYN Flag Count",
    "Bwd Packet Length Mean",
)

FEATURE_GROUPS: dict[str, dict[str, list[str]]] = {
    "unsw_nb15": {
        "completo": [],
        "sin TTL (sttl, dttl, ct_state_ttl)": ["sttl", "dttl", "ct_state_ttl"],
        "sin state": ["state"],
        "sin TTL ni state": ["sttl", "dttl", "ct_state_ttl", "state"],
        "sin categoricas (proto, service, state)": ["proto", "service", "state"],
    },
    "cicids2017": {
        "completo": [],
        "sin Destination Port": ["Destination Port"],
        "sin atajos de Engelen et al. (2021)": list(ENGELEN_SHORTCUTS),
    },
}

# ---------------------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------------------


def _read_summary(dataset: config.DatasetSource) -> dict[str, Any]:
    path = dataset.reports_dir / "training_summary.json"
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def improved_params(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Hyperparameters found by the main search, per algorithm (`clf__` prefixed)."""
    return {a: dict(summary["models"][f"{a}_improved"]["best_params"]) for a in ("rf", "xgb")}


def fit_pipeline(
    algorithm: str,
    improved: bool,
    params: dict[str, Any],
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int,
) -> Any:
    """Fit one pipeline; `params` only applies to the improved version."""
    numeric, categorical = split_column_types(X)
    pipeline = build_pipeline(algorithm, numeric, categorical, improved, random_state)  # type: ignore[arg-type]
    if improved and params:
        pipeline.set_params(**params)
    return pipeline.fit(X, y)


def seed_rows(df: pd.DataFrame, seed: int, params: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Split with `seed`, fit the six models and return their metric rows (long format)."""
    splits = make_splits(df, random_state=seed)
    trained: dict[str, TrainedModel] = {}
    for algorithm in ("rf", "xgb"):
        for variant in ("baseline", "improved"):
            improved = variant == "improved"
            model = fit_pipeline(
                algorithm, improved, params[algorithm], splits.train.X, splits.train.y, seed
            )
            name = f"{algorithm}_{variant}"
            trained[name] = TrainedModel(name, algorithm, variant, model)
    for variant in ("baseline", "improved"):
        mix = build_mix(trained, variant)
        trained[mix.name] = mix
    rows, _, _ = evaluate_models(
        list(trained.values()), splits, config.RECALL_TARGET, config.FPR_TARGET
    )
    for row in rows:
        row["seed"] = seed
    return rows


def summarize_seeds(rows: pd.DataFrame) -> pd.DataFrame:
    """Mean, sample standard deviation, min and max over seeds, on the test split."""
    test = rows[rows["split"] == "test"]
    grouped = test.groupby(["model", "operating_point"], sort=False)[list(SUMMARY_METRICS)]
    summary = grouped.agg(["mean", "std", "min", "max"])
    summary.columns = ["_".join(map(str, column)) for column in summary.columns]
    summary["n_seeds"] = grouped.size()
    return summary.reset_index()


def best_by_seed(rows: pd.DataFrame) -> dict[str, dict[str, str]]:
    """Which model wins in every seed under the AGENT.md rule and under the FPR budget."""
    wins: dict[str, dict[str, str]] = {}
    for seed, group in rows.groupby("seed"):
        records = [{str(k): v for k, v in row.items()} for row in group.to_dict("records")]
        wins[str(seed)] = {
            "recall_target": select_best(records, config.RECALL_TARGET),
            "fpr_budget": select_best_for_budget(records),
        }
    return wins


# ---------------------------------------------------------------------------------------
# Task: seeds
# ---------------------------------------------------------------------------------------


def run_seeds(
    dataset_key: str, seeds: Sequence[int] = SEEDS, recompute_primary: bool = False
) -> pd.DataFrame:
    """Repeat the protocol for every seed. Seed 42 is read from `metrics.csv` by default."""
    dataset = config.get_dataset(dataset_key)
    df = load_processed(dataset_key)
    params = improved_params(_read_summary(dataset))
    stored = pd.read_csv(dataset.reports_dir / "metrics.csv").drop(columns=["dataset"])
    stored["seed"] = config.RANDOM_STATE

    # Finished seeds are kept in a partial file so an interrupted run resumes instead of restarting.
    partial_path = dataset.reports_dir / "multiseed.partial.csv"
    done = pd.read_csv(partial_path) if partial_path.is_file() else pd.DataFrame()
    finished = set(done["seed"].unique()) if len(done) else set()
    frames: list[pd.DataFrame] = []
    reproducibility: dict[str, float] | None = None
    for seed in seeds:
        if seed == config.RANDOM_STATE and not recompute_primary:
            frames.append(stored)
            continue
        if seed in finished:
            logger.info("seed %d already done, reused from the partial file", seed)
            frames.append(done[done["seed"] == seed])
            continue
        started = time.perf_counter()
        fresh = pd.DataFrame(seed_rows(df, seed, params))
        logger.info("seed %d done in %.0fs", seed, time.perf_counter() - started)
        pd.concat([done, fresh], ignore_index=True).to_csv(partial_path, index=False)
        done = pd.read_csv(partial_path)
        if seed == config.RANDOM_STATE:
            key = ["model", "operating_point", "split"]
            merged = stored.merge(fresh, on=key, suffixes=("_stored", "_fresh"))
            diffs = [
                float((merged[f"{m}_stored"] - merged[f"{m}_fresh"]).abs().max())
                for m in ("recall", "fpr", "precision", "roc_auc")
            ]
            reproducibility = {"max_abs_difference": max(diffs)}
        frames.append(fresh)
    rows = pd.concat(frames, ignore_index=True)
    rows.to_csv(dataset.reports_dir / "multiseed.csv", index=False)
    partial_path.unlink(missing_ok=True)
    summary = summarize_seeds(rows)
    summary.to_csv(dataset.reports_dir / "multiseed_summary.csv", index=False)
    info = {
        "seeds": list(seeds),
        "hyperparameters_from_seed": config.RANDOM_STATE,
        "best_by_seed": best_by_seed(rows),
        "primary_reproduction": reproducibility,
    }
    (dataset.reports_dir / "multiseed_summary.json").write_text(
        json.dumps(info, indent=2), encoding="utf-8"
    )
    return rows


# ---------------------------------------------------------------------------------------
# Task: pairwise
# ---------------------------------------------------------------------------------------


def run_pairwise(dataset_key: str, n_boot: int = 2000) -> pd.DataFrame:
    """Paired bootstrap tests on the saved test scores of the main run."""
    dataset = config.get_dataset(dataset_key)
    summary = _read_summary(dataset)
    saved = np.load(dataset.models_dir / "scores.npz")
    y = saved["y_test"]
    records: list[dict[str, Any]] = []
    for a, b in PAIRS:
        for point in OPERATING_POINTS:
            result = paired_bootstrap_difference(
                y,
                saved[f"{a}_test"],
                summary["thresholds"][a][point],
                saved[f"{b}_test"],
                summary["thresholds"][b][point],
                n_boot=n_boot,
            )
            for metric, values in result.items():
                records.append(
                    {"model_a": a, "model_b": b, "operating_point": point, "metric": metric, **values}
                )
    table = pd.DataFrame(records)
    table.to_csv(dataset.reports_dir / "pairwise_tests.csv", index=False)
    return table


# ---------------------------------------------------------------------------------------
# Task: official UNSW-NB15 partitions
# ---------------------------------------------------------------------------------------


def split_official_partitions(frames: Sequence[pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (training, testing) from the two raw partitions, assigned by row count.

    The mirror swaps the file names, so the larger partition (175,341 rows) is the official
    training set and the smaller one (82,332 rows) the official testing set.
    """
    if len(frames) != 2:
        raise ValueError(f"Expected two UNSW-NB15 partitions, found {len(frames)}.")
    train, test = sorted(frames, key=len, reverse=True)
    return train, test


def load_official_partitions(raw_dir: Path = config.UNSW_NB15.raw_dir) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the two CSV files and return the (training, testing) partitions, normalised."""
    frames = []
    for path in sorted(raw_dir.glob("*.csv")):
        frame = pd.read_csv(path, encoding="utf-8-sig")
        frame.columns = [str(c).strip() for c in frame.columns]
        frames.append(frame)
    train, test = split_official_partitions(frames)
    return normalize_unsw(train), normalize_unsw(test)


def seen_mask(train_X: pd.DataFrame, test_X: pd.DataFrame) -> np.ndarray:
    """True for the test rows whose exact feature vector also occurs in the training rows."""
    seen = set(pd.util.hash_pandas_object(train_X, index=False).to_numpy().tolist())
    hashes = pd.util.hash_pandas_object(test_X, index=False).to_numpy().tolist()
    return np.fromiter((h in seen for h in hashes), dtype=bool, count=len(hashes))


def _cleaned(raw: pd.DataFrame, dedup: bool) -> pd.DataFrame:
    frame, _ = clean(
        raw,
        config.UNSW_NB15.categorical_columns,
        config.UNSW_NB15.key,
        drop_duplicates=dedup,
        drop_conflicting=dedup,
    )
    return frame


def _score_row(y: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    metrics = compute_metrics(y, scores, 0.5)
    return {
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "fpr": metrics.fpr,
        "f1": metrics.f1,
        "roc_auc": metrics.roc_auc,
        "pr_auc": metrics.pr_auc,
    }


def _align(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep the same columns, in the same order, in both partitions."""
    columns = [c for c in train.columns if c in test.columns]
    return train[columns], test[columns]


def official_rows(train_raw: pd.DataFrame, test_raw: pd.DataFrame, n_folds: int = 5) -> list[dict[str, Any]]:
    """Protocols A, B (official train/test) and C (CV on the training partition)."""
    records: list[dict[str, Any]] = []
    for protocol, dedup in (("A_oficial_ingenuo", False), ("B_oficial_depurado", True)):
        train, test = _align(_cleaned(train_raw, dedup), _cleaned(test_raw, dedup))
        X_train, y_train, _ = split_features_target(train)
        X_test, y_test, _ = split_features_target(test)
        if dedup:
            keep = ~seen_mask(X_train, X_test)
            X_test, y_test = X_test[keep], y_test[keep]
        leaked = float(seen_mask(X_train, X_test).mean())
        for algorithm in ("rf", "xgb"):
            model = fit_pipeline(algorithm, False, {}, X_train, y_train, config.RANDOM_STATE)
            scores = attack_scores(model, X_test)
            records.append(
                {
                    "protocol": protocol,
                    "model": f"{algorithm}_baseline",
                    "fold": "",
                    "n_train": len(X_train),
                    "n_test": len(X_test),
                    "leaked_test_share": leaked,
                    **_score_row(y_test.to_numpy(), scores),
                }
            )
    for protocol, dedup in (("C_cv5_ingenuo", False), ("C_cv5_depurado", True)):
        train = _cleaned(train_raw, dedup)
        X, y, attack = split_features_target(train)
        folds = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=config.RANDOM_STATE)
        for fold, (fit_index, test_index) in enumerate(folds.split(X, attack)):
            X_fit, X_hold = X.iloc[fit_index], X.iloc[test_index]
            y_fit, y_hold = y.iloc[fit_index], y.iloc[test_index]
            leaked = float(seen_mask(X_fit, X_hold).mean())
            for algorithm in ("rf", "xgb"):
                model = fit_pipeline(algorithm, False, {}, X_fit, y_fit, config.RANDOM_STATE)
                scores = attack_scores(model, X_hold)
                records.append(
                    {
                        "protocol": protocol,
                        "model": f"{algorithm}_baseline",
                        "fold": fold,
                        "n_train": len(X_fit),
                        "n_test": len(X_hold),
                        "leaked_test_share": leaked,
                        **_score_row(y_hold.to_numpy(), scores),
                    }
                )
    return records


def run_official() -> pd.DataFrame:
    """Run the official-partition protocols and save `official_partitions.csv`."""
    dataset = config.UNSW_NB15
    train_raw, test_raw = load_official_partitions(dataset.raw_dir)
    logger.info("official partitions: train %d rows, test %d rows", len(train_raw), len(test_raw))
    table = pd.DataFrame(official_rows(train_raw, test_raw))
    dataset.reports_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(dataset.reports_dir / "official_partitions.csv", index=False)
    return table


# ---------------------------------------------------------------------------------------
# Task: feature ablation
# ---------------------------------------------------------------------------------------


def drop_feature_group(X: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
    """Drop the named columns; every name must exist so a typo cannot silently do nothing."""
    missing = [c for c in columns if c not in X.columns]
    if missing:
        raise KeyError(f"Columns not found: {missing}")
    return X.drop(columns=list(columns))


def ablation_rows(
    df: pd.DataFrame,
    groups: dict[str, list[str]],
    params: dict[str, Any],
    seed: int = config.RANDOM_STATE,
) -> list[dict[str, Any]]:
    """Refit the improved XGBoost without each group and score it at the three points."""
    splits = make_splits(df, random_state=seed)
    y_val, y_test = splits.val.y.to_numpy(), splits.test.y.to_numpy()
    records: list[dict[str, Any]] = []
    for group, columns in groups.items():
        present = [c for c in columns if c in splits.train.X.columns]
        X_train = drop_feature_group(splits.train.X, present)
        model = fit_pipeline("xgb", True, params, X_train, splits.train.y, seed)
        val_scores = attack_scores(model, drop_feature_group(splits.val.X, present))
        test_scores = attack_scores(model, drop_feature_group(splits.test.X, present))
        thresholds = choose_thresholds(y_val, val_scores, config.RECALL_TARGET, config.FPR_TARGET)
        for row in metric_rows("xgb_improved", y_val, y_test, val_scores, test_scores, thresholds):
            if row["split"] == "test":
                records.append({"group": group, "dropped": "; ".join(present), **row})
        logger.info("ablation '%s' done (%d columns dropped)", group, len(present))
    return records


def run_features(dataset_key: str) -> pd.DataFrame:
    """Run the feature ablation and save `feature_ablation.csv`."""
    dataset = config.get_dataset(dataset_key)
    df = load_processed(dataset_key)
    params = improved_params(_read_summary(dataset))["xgb"]
    table = pd.DataFrame(ablation_rows(df, FEATURE_GROUPS[dataset_key], params))
    table.to_csv(dataset.reports_dir / "feature_ablation.csv", index=False)
    return table


# ---------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Formal experiments for the final report.")
    parser.add_argument("--dataset", choices=list(config.DATASETS), required=True)
    parser.add_argument(
        "--task", choices=["seeds", "pairwise", "official", "features", "all"], default="all"
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    parser.add_argument(
        "--recompute-primary",
        action="store_true",
        help="refit seed 42 as well and report how closely it reproduces the stored metrics",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    tasks = ["pairwise", "official", "features", "seeds"] if args.task == "all" else [args.task]
    for task in tasks:
        started = time.perf_counter()
        if task == "seeds":
            run_seeds(args.dataset, args.seeds, args.recompute_primary)
        elif task == "pairwise":
            run_pairwise(args.dataset)
        elif task == "official":
            if args.dataset != config.UNSW_NB15.key:
                logger.info("official partitions exist only for unsw_nb15, skipped")
                continue
            run_official()
        else:
            run_features(args.dataset)
        logger.info("task %s finished in %.0fs", task, time.perf_counter() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())
