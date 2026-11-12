"""Data helpers for the visual demo (`streamlit run app/demo_app.py`).

Everything here is plain pandas/numpy so it can be unit tested without Streamlit.

Usage:
    python -m src.demo --dataset cicids2017 --write-examples
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve

from src import config
from src.data_loader import load_processed, make_splits
from src.evaluate import MODEL_ORDER, OPERATING_POINTS, detection_by_attack_type, pretty
from src.metrics import Metrics, compute_metrics
from src.predict import classify, load_bundle

logger = logging.getLogger(__name__)

DEMO_DIR = config.PROJECT_ROOT / "docs" / "demo"
EXAMPLE_FILES = {
    "unsw_nb15": DEMO_DIR / "flujos_ejemplo.csv",
    "cicids2017": DEMO_DIR / "flujos_ejemplo_cicids2017.csv",
}
NOTE_COLUMN = "nota"
RANDOM_NOTE = "muestra aleatoria"
FALSE_ALARM_NOTE = "elegido: falsa alarma solo con el umbral de Recall 0.95"
FALSE_ALARM_DEFAULT_NOTE = "elegido: falsa alarma con umbral 0.5 que el umbral de Recall 0.95 evita"
MISSED_NOTE = "elegido: ataque ({family}) que se escapa"

OUTCOME_LABELS = {
    (1, 1): "Ataque detectado",
    (0, 0): "Normal correcto",
    (0, 1): "Falsa alarma",
    (1, 0): "Ataque no detectado",
}


@dataclass(frozen=True)
class DemoContext:
    """Every artifact the demo needs for one dataset."""

    dataset: config.DatasetSource
    bundle: dict[str, Any]
    scores: dict[str, np.ndarray]
    summary: dict[str, Any]
    metrics: pd.DataFrame
    ablation: dict[str, Any] | None
    cleaning: dict[str, Any] | None

    @property
    def best_model(self) -> str:
        return str(self.summary["best_model"])


def required_artifacts(dataset_key: str) -> dict[str, Path]:
    """Files that must exist before the demo can show a dataset."""
    dataset = config.get_dataset(dataset_key)
    return {
        "model": dataset.models_dir / "best_model.joblib",
        "scores": dataset.models_dir / "scores.npz",
        "summary": dataset.reports_dir / "training_summary.json",
        "metrics": dataset.reports_dir / "metrics.csv",
    }


def missing_artifacts(dataset_key: str) -> list[Path]:
    return [path for path in required_artifacts(dataset_key).values() if not path.is_file()]


def _read_json(path: Path) -> dict[str, Any] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_demo_context(dataset_key: str) -> DemoContext:
    """Load the model bundle, saved scores and reports of a dataset."""
    missing = missing_artifacts(dataset_key)
    if missing:
        raise FileNotFoundError(
            f"Missing {', '.join(str(p) for p in missing)}. "
            f"Run `python -m src.train --dataset {dataset_key}` first."
        )
    dataset = config.get_dataset(dataset_key)
    paths = required_artifacts(dataset_key)
    with np.load(paths["scores"]) as saved:
        scores = {name: saved[name] for name in saved.files}
    summary = _read_json(paths["summary"])
    assert summary is not None
    return DemoContext(
        dataset=dataset,
        bundle=load_bundle(dataset_key),
        scores=scores,
        summary=summary,
        metrics=pd.read_csv(paths["metrics"]),
        ablation=_read_json(dataset.reports_dir / "leakage_ablation.json"),
        cleaning=_read_json(dataset.cleaning_report_file),
    )


def metrics_at_threshold(scores: dict[str, np.ndarray], model: str, threshold: float) -> Metrics:
    """Test set metrics of a model at an arbitrary decision threshold."""
    return compute_metrics(scores["y_test"], scores[f"{model}_test"], threshold)


def meets_criterion(metrics: Metrics) -> bool:
    """AGENT.md section 6: Recall >= 0.95 and FPR <= 0.02 at the same time."""
    return metrics.recall >= config.RECALL_TARGET and metrics.fpr <= config.FPR_TARGET


def roc_points(scores: dict[str, np.ndarray], model: str, max_points: int = 400) -> pd.DataFrame:
    """ROC curve of a model on the test set, thinned to at most `max_points` rows."""
    fpr, tpr, thresholds = roc_curve(scores["y_test"], scores[f"{model}_test"])
    keep = np.unique(np.linspace(0, len(fpr) - 1, min(max_points, len(fpr))).astype(int))
    return pd.DataFrame(
        {
            "fpr": fpr[keep],
            "recall": tpr[keep],
            "threshold": np.clip(thresholds[keep], 0.0, 1.0),
        }
    )


def family_detection(scores: dict[str, np.ndarray], model: str, threshold: float) -> pd.DataFrame:
    """Share of test flows flagged as attack per family at one threshold.

    For BENIGN the share is the false positive rate; for the rest, the detection rate.
    """
    families = pd.Series(scores["attack_test"], name="family")
    flagged = pd.Series(scores[f"{model}_test"] >= threshold)
    table = flagged.groupby(families).agg(flagged_share="mean", n="size").reset_index()
    return table.sort_values("flagged_share").reset_index(drop=True)


def family_table(context: DemoContext, model: str | None = None) -> pd.DataFrame:
    """Per family detection at the three stored operating points (see `src.evaluate`)."""
    name = model or context.best_model
    return detection_by_attack_type(context.scores, name, context.summary["thresholds"][name])


def cleaning_funnel(report: dict[str, Any]) -> pd.DataFrame:
    """Rows kept and removed by each cleaning step, in the order they are applied."""
    steps = [
        ("Infinitos o NaN", int(report["rows_removed_missing"])),
        ("Duplicados", int(report["rows_removed_duplicates"])),
        ("Contradictorios", int(report["rows_removed_conflicting"])),
        ("Flujos limpios", int(report["rows_final"])),
    ]
    frame = pd.DataFrame(steps, columns=["step", "rows"])
    frame["share"] = frame["rows"] / max(int(report["rows_raw"]), 1)
    return frame


def model_comparison(metrics: pd.DataFrame, split: str = "test") -> pd.DataFrame:
    """One row per model and operating point, in the canonical model order."""
    frame = metrics[metrics["split"] == split].copy()
    frame["model_label"] = frame["model"].map(pretty)
    frame["order"] = frame["model"].map(MODEL_ORDER.index)
    frame["point_order"] = frame["operating_point"].map(OPERATING_POINTS.index)
    return frame.sort_values(["order", "point_order"]).drop(columns=["order", "point_order"])


def judge(predictions: pd.DataFrame, flows: pd.DataFrame) -> pd.DataFrame:
    """Add the real class and the outcome of each prediction when the flows carry labels."""
    result = predictions.copy()
    if config.LABEL_COLUMN not in flows.columns:
        return result
    real = pd.to_numeric(flows[config.LABEL_COLUMN], errors="coerce").fillna(0).astype(int)
    if config.ATTACK_TYPE_COLUMN in flows.columns:
        result["real"] = flows[config.ATTACK_TYPE_COLUMN].astype(str).to_numpy()
    else:
        result["real"] = np.where(real == 1, "Ataque", config.BENIGN_LABEL)
    result["outcome"] = [
        OUTCOME_LABELS[(int(r), int(p))] for r, p in zip(real, result["prediction"])
    ]
    result["correct"] = real.to_numpy() == result["prediction"].to_numpy()
    return result


def build_example_flows(
    test: pd.DataFrame,
    bundle: dict[str, Any],
    n_normal: int = 4,
    n_attack: int = 4,
    seed: int = config.RANDOM_STATE,
) -> pd.DataFrame:
    """Pick demo flows from the test partition: random ones plus two chosen mistakes.

    `test` holds the feature columns plus `label` and `attack_type`. Attacks are drawn
    from distinct families while possible. The chosen rows are a benign flow flagged at only
    one of the default and recall_target thresholds and an attack missed at every operating point; either
    is skipped when the model makes no such mistake.
    """
    rng = np.random.default_rng(seed)
    probability = classify(test, bundle, "default")["attack_probability"].to_numpy()
    label = test[config.LABEL_COLUMN].to_numpy()
    thresholds = bundle["thresholds"]

    normal_pool = np.flatnonzero(label == 0)
    picked = list(rng.choice(normal_pool, size=min(n_normal, len(normal_pool)), replace=False))
    attacks = test.loc[label == 1, config.ATTACK_TYPE_COLUMN]
    families = attacks.value_counts().index.tolist()
    for i in range(min(n_attack, len(attacks))):
        family = families[i % len(families)]
        pool = np.flatnonzero((label == 1) & (test[config.ATTACK_TYPE_COLUMN] == family).to_numpy())
        pool = np.setdiff1d(pool, picked)
        if len(pool):
            picked.append(int(rng.choice(pool)))
    notes = [RANDOM_NOTE] * len(picked)

    low = min(thresholds["recall_target"], thresholds["default"])
    high = max(thresholds["recall_target"], thresholds["default"])
    false_alarms = np.setdiff1d(
        np.flatnonzero((label == 0) & (probability >= low) & (probability < high)), picked
    )
    if len(false_alarms):
        picked.append(int(false_alarms[np.argmax(probability[false_alarms])]))
        lowered = thresholds["recall_target"] < thresholds["default"]
        notes.append(FALSE_ALARM_NOTE if lowered else FALSE_ALARM_DEFAULT_NOTE)
    missed = np.setdiff1d(
        np.flatnonzero((label == 1) & (probability < min(thresholds.values()))), picked
    )
    if len(missed):
        chosen = int(missed[np.argmax(probability[missed])])
        picked.append(chosen)
        notes.append(MISSED_NOTE.format(family=test[config.ATTACK_TYPE_COLUMN].iloc[chosen]))

    examples = test.iloc[picked].reset_index(drop=True)
    examples[NOTE_COLUMN] = notes
    return examples


def write_examples(dataset_key: str, path: Path | None = None) -> Path:
    """Regenerate the example flows of a dataset from its test partition."""
    path = path or EXAMPLE_FILES[dataset_key]
    partition = make_splits(load_processed(dataset_key)).test
    test = partition.X.copy()
    test[config.LABEL_COLUMN] = partition.y
    test[config.ATTACK_TYPE_COLUMN] = partition.attack
    examples = build_example_flows(test, load_bundle(dataset_key))
    path.parent.mkdir(parents=True, exist_ok=True)
    examples.to_csv(path, index=False)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Helpers for the visual demo.")
    parser.add_argument("--dataset", choices=list(config.DATASETS), required=True)
    parser.add_argument(
        "--write-examples", action="store_true", help="regenerate the example flows CSV"
    )
    parser.add_argument("--output", type=Path, help="where to write the example flows")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.write_examples:
        logger.info("Wrote %s", write_examples(args.dataset, args.output))
    else:
        missing = missing_artifacts(args.dataset)
        logger.info("Missing artifacts: %s", [str(p) for p in missing] or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
