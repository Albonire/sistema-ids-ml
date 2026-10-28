"""Inference engine: classify a file of flows or a single flow with the trained model.

Usage:
    python -m src.predict --dataset unsw_nb15 --input flows.csv [--output predictions.csv]
    python -m src.predict --dataset cicids2017 --json '{"Destination Port": 80, ...}'
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from src import config
from src.models import attack_scores

NORMAL_TEXT = "Trafico Normal"
ATTACK_TEXT = "Ataque Detectado"

logger = logging.getLogger(__name__)


def load_bundle(dataset: str = "cicids2017", path: Path | None = None) -> dict[str, Any]:
    """Load the persisted best model of a dataset (written by `python -m src.train`)."""
    path = path or config.get_dataset(dataset).models_dir / "best_model.joblib"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found. Run `python -m src.train --dataset {dataset}` first.")
    return joblib.load(path)


def prepare_features(flows: pd.DataFrame, bundle: dict[str, Any]) -> pd.DataFrame:
    """Select, order and validate the feature columns expected by the model.

    Column names are stripped (raw CICIDS2017 headers have leading spaces), extra columns
    such as labels are ignored, and rows with missing or infinite values are rejected.
    """
    frame = flows.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    columns: list[str] = bundle["feature_columns"]
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"Input is missing {len(missing)} required columns: {missing[:5]}...")
    features = frame[columns].copy()
    for column in bundle["numeric_columns"]:
        features[column] = pd.to_numeric(features[column], errors="coerce").astype("float32")
    for column in bundle["categorical_columns"]:
        features[column] = features[column].astype(str).str.strip()
    numeric = features[bundle["numeric_columns"]].to_numpy(dtype="float64")
    invalid = ~np.isfinite(numeric).all(axis=1)
    if invalid.any():
        raise ValueError(
            f"{int(invalid.sum())} rows contain missing, non numeric or infinite values "
            "(first row index: " + str(int(np.flatnonzero(invalid)[0])) + ")."
        )
    return features


def classify(
    flows: pd.DataFrame, bundle: dict[str, Any], operating_point: str = "recall_target"
) -> pd.DataFrame:
    """Return one row per flow with the decision, the text label and the attack probability.

    `operating_point` selects the stored decision threshold: "default" (0.5),
    "recall_target" (minimum FPR with Recall >= 0.95) or "fpr_budget" (maximum Recall
    with FPR <= 0.02).
    """
    features = prepare_features(flows, bundle)
    probability = attack_scores(bundle["model"], features)
    is_attack = probability >= bundle["thresholds"][operating_point]
    return pd.DataFrame(
        {
            "prediction": is_attack.astype("int8"),
            "classification": np.where(is_attack, ATTACK_TEXT, NORMAL_TEXT),
            "attack_probability": probability,
        },
        index=flows.index,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify network flows as normal or attack.")
    parser.add_argument("--dataset", choices=list(config.DATASETS), required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="CSV file with one flow per row")
    source.add_argument("--json", dest="json_flow", help="a single flow as a JSON object")
    parser.add_argument("--output", type=Path, help="write batch predictions to this CSV")
    parser.add_argument("--model", type=Path, help="path to a model bundle (default: best model)")
    parser.add_argument(
        "--operating-point",
        choices=["default", "recall_target", "fpr_budget"],
        default="recall_target",
        help="which stored decision threshold to apply",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    bundle = load_bundle(args.dataset, args.model)
    if args.json_flow is not None:
        result = classify(
            pd.DataFrame([json.loads(args.json_flow)]), bundle, args.operating_point
        ).iloc[0]
        print(
            json.dumps(
                {
                    "classification": result["classification"],
                    "attack_probability": round(float(result["attack_probability"]), 6),
                    "operating_point": args.operating_point,
                    "threshold": round(float(bundle["thresholds"][args.operating_point]), 6),
                    "model": bundle["model_name"],
                },
                indent=2,
            )
        )
        return 0

    flows = pd.read_csv(args.input, encoding="utf-8-sig", skipinitialspace=True)
    predictions = classify(flows, bundle, args.operating_point)
    counts = predictions["classification"].value_counts().to_dict()
    logger.info(
        "Model %s, %s threshold %.4f: %s",
        bundle["model_name"],
        args.operating_point,
        bundle["thresholds"][args.operating_point],
        counts,
    )
    if args.output:
        predictions.to_csv(args.output, index=False)
        logger.info("Wrote %s", args.output)
    else:
        print(predictions.head(20).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
