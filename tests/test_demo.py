from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import config, demo
from src.metrics import compute_metrics


class FixedScores:
    """Model stub whose attack probability is the `score` feature itself."""

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = X["score"].to_numpy(dtype="float64")
        return np.column_stack([1 - p, p])


@pytest.fixture
def scores() -> dict[str, np.ndarray]:
    rng = np.random.default_rng(0)
    y = np.array([0] * 60 + [1] * 40)
    values = np.clip(np.where(y == 1, 0.7, 0.3) + rng.normal(0, 0.2, size=100), 0, 1)
    families = np.where(y == 0, "BENIGN", np.where(np.arange(100) % 2 == 0, "DoS", "Probe"))
    return {"y_test": y, "attack_test": families, "xgb_improved_test": values}


def test_metrics_at_threshold_matches_compute_metrics(scores: dict[str, np.ndarray]) -> None:
    result = demo.metrics_at_threshold(scores, "xgb_improved", 0.42)
    assert result == compute_metrics(scores["y_test"], scores["xgb_improved_test"], 0.42)
    assert result.tp + result.fn == 40 and result.tn + result.fp == 60


def test_meets_criterion_requires_both_targets(scores: dict[str, np.ndarray]) -> None:
    perfect = compute_metrics(scores["y_test"], scores["y_test"].astype(float), 0.5)
    assert demo.meets_criterion(perfect)
    everything_flagged = demo.metrics_at_threshold(scores, "xgb_improved", 0.0)
    assert everything_flagged.recall == 1.0 and not demo.meets_criterion(everything_flagged)


def test_roc_points_are_bounded_and_monotonic(scores: dict[str, np.ndarray]) -> None:
    curve = demo.roc_points(scores, "xgb_improved", max_points=20)
    assert len(curve) <= 20
    assert curve["fpr"].is_monotonic_increasing and curve["recall"].is_monotonic_increasing
    assert curve["threshold"].between(0, 1).all()
    assert curve[["fpr", "recall"]].iloc[-1].tolist() == [1.0, 1.0]


def test_family_detection_reports_share_and_support(scores: dict[str, np.ndarray]) -> None:
    table = demo.family_detection(scores, "xgb_improved", 0.5).set_index("family")
    assert table["n"].to_dict() == {"BENIGN": 60, "DoS": 20, "Probe": 20}
    metrics = demo.metrics_at_threshold(scores, "xgb_improved", 0.5)
    assert table.loc["BENIGN", "flagged_share"] == pytest.approx(metrics.fpr)


def test_cleaning_funnel_accounts_for_every_raw_row() -> None:
    report = {
        "rows_raw": 100,
        "rows_removed_missing": 5,
        "rows_removed_duplicates": 30,
        "rows_removed_conflicting": 2,
        "rows_final": 63,
    }
    funnel = demo.cleaning_funnel(report)
    assert funnel["rows"].sum() == 100
    assert funnel["share"].sum() == pytest.approx(1.0)
    assert funnel["step"].iloc[-1] == "Flujos limpios"


def test_model_comparison_keeps_split_and_canonical_order() -> None:
    rows = [
        {"model": model, "operating_point": point, "split": split, "recall": 0.9, "fpr": 0.1}
        for model in ("xgb_improved", "rf_baseline")
        for point in ("fpr_budget", "default")
        for split in ("val", "test")
    ]
    table = demo.model_comparison(pd.DataFrame(rows))
    assert set(table["split"]) == {"test"}
    assert table["model"].tolist() == ["rf_baseline"] * 2 + ["xgb_improved"] * 2
    assert table["operating_point"].tolist()[:2] == ["default", "fpr_budget"]
    assert table["model_label"].iloc[0] == "Random Forest (base)"


def test_judge_labels_each_outcome() -> None:
    predictions = pd.DataFrame({"prediction": [1, 0, 1, 0]})
    flows = pd.DataFrame(
        {"label": [1, 0, 0, 1], "attack_type": ["DoS", "BENIGN", "BENIGN", "Probe"]}
    )
    judged = demo.judge(predictions, flows)
    assert judged["outcome"].tolist() == [
        "Ataque detectado",
        "Normal correcto",
        "Falsa alarma",
        "Ataque no detectado",
    ]
    assert judged["correct"].tolist() == [True, True, False, False]
    assert "outcome" not in demo.judge(predictions, pd.DataFrame({"x": [1, 2, 3, 4]}))


def test_build_example_flows_picks_random_rows_and_both_mistakes() -> None:
    rng = np.random.default_rng(1)
    label = np.array([0] * 50 + [1] * 50)
    score = np.where(label == 1, 0.9, 0.05).astype("float64")
    score[3] = 0.45  # benign flagged only below the default threshold
    score[60] = 0.10  # attack missed at every operating point
    test = pd.DataFrame(
        {
            "score": score,
            "other": rng.normal(size=100),
            "label": label,
            "attack_type": np.where(label == 0, "BENIGN", np.where(np.arange(100) % 2, "DoS", "Probe")),
        }
    )
    bundle = {
        "model": FixedScores(),
        "feature_columns": ["score", "other"],
        "numeric_columns": ["score", "other"],
        "categorical_columns": [],
        "thresholds": {"default": 0.5, "recall_target": 0.3, "fpr_budget": 0.7},
    }
    examples = demo.build_example_flows(test, bundle, n_normal=4, n_attack=4)

    assert len(examples) == 10 and not examples.duplicated(["score", "other"]).any()
    random_rows = examples[examples[demo.NOTE_COLUMN] == demo.RANDOM_NOTE]
    assert random_rows["label"].tolist() == [0] * 4 + [1] * 4
    assert set(random_rows["attack_type"]) == {"BENIGN", "DoS", "Probe"}
    false_alarm, missed = examples.iloc[-2], examples.iloc[-1]
    assert false_alarm["label"] == 0 and false_alarm["score"] == pytest.approx(0.45)
    assert missed["label"] == 1 and missed["score"] == pytest.approx(0.10)
    assert "escapa" in missed[demo.NOTE_COLUMN]


def test_missing_artifacts_and_context_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    assert len(demo.missing_artifacts("cicids2017")) == 4
    with pytest.raises(FileNotFoundError, match="src.train --dataset cicids2017"):
        demo.load_demo_context("cicids2017")
