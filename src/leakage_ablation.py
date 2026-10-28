"""Quantify how much duplicated rows inflate test metrics.

Usage:
    python -m src.leakage_ablation --dataset unsw_nb15|cicids2017

The same baseline XGBoost (Entregable 1, section 8.4) is trained and tested under three data
protocols that differ only in how rows are cleaned before the stratified 70/15/15 split:

- naive: only mandatory cleaning (infinite or missing values), duplicates kept.
- dedup: exact duplicate rows removed.
- full: duplicates and rows whose feature vector has conflicting labels removed (this project).

`leaked_test_share` is the fraction of test rows whose exact feature vector also appears in the
training partition, i.e. rows the model can answer by memorisation.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

import numpy as np
import pandas as pd

from src import config
from src.data_loader import make_splits, split_features_target
from src.features import split_column_types
from src.metrics import compute_metrics
from src.models import attack_scores, build_pipeline
from src.preprocess import clean, load_raw, load_raw_unsw

logger = logging.getLogger(__name__)

PROTOCOLS: dict[str, dict[str, bool]] = {
    "naive": {"drop_duplicates": False, "drop_conflicting": False},
    "dedup": {"drop_duplicates": True, "drop_conflicting": False},
    "full": {"drop_duplicates": True, "drop_conflicting": True},
}


def leaked_share(train_X: pd.DataFrame, test_X: pd.DataFrame) -> float:
    """Share of test rows whose exact feature vector is present in the training rows."""
    train_hashes = set(pd.util.hash_pandas_object(train_X, index=False).to_numpy().tolist())
    test_hashes = pd.util.hash_pandas_object(test_X, index=False).to_numpy().tolist()
    return float(np.mean([h in train_hashes for h in test_hashes]))


def evaluate_protocol(df: pd.DataFrame) -> dict[str, Any]:
    """Train the baseline XGBoost on a processed frame and score it on its test split."""
    splits = make_splits(df)
    numeric, categorical = split_column_types(splits.train.X)
    model = build_pipeline("xgb", numeric, categorical, improved=False).fit(
        splits.train.X, splits.train.y
    )
    scores = attack_scores(model, splits.test.X)
    metrics = compute_metrics(splits.test.y.to_numpy(), scores, 0.5)
    return {
        "rows": len(df),
        "test_rows": len(splits.test),
        "leaked_test_share": leaked_share(splits.train.X, splits.test.X),
        "accuracy": metrics.accuracy,
        "recall": metrics.recall,
        "fpr": metrics.fpr,
        "f1": metrics.f1,
    }


def run(dataset_key: str) -> dict[str, dict[str, Any]]:
    dataset = config.get_dataset(dataset_key)
    raw = load_raw_unsw(dataset.raw_dir) if dataset is config.UNSW_NB15 else load_raw(dataset.raw_dir)
    results: dict[str, dict[str, Any]] = {}
    for name, options in PROTOCOLS.items():
        cleaned, _ = clean(raw, dataset.categorical_columns, dataset.key, **options)
        results[name] = evaluate_protocol(cleaned)
        logger.info("%s: %s", name, results[name])
    out = dataset.reports_dir / "leakage_ablation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Duplicate leakage ablation.")
    parser.add_argument("--dataset", choices=list(config.DATASETS), required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(args.dataset)
    return 0


if __name__ == "__main__":
    sys.exit(main())
