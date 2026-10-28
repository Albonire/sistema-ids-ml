from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification

from src import config, evaluate, predict, train
from src.data_loader import make_splits
from src.models import SoftVotingEnsemble, attack_scores


@pytest.fixture
def tiny_dataset() -> pd.DataFrame:
    """Synthetic processed dataset with a categorical column and three attack types."""
    X, y = make_classification(
        n_samples=1200, n_features=8, n_informative=5, n_redundant=2, weights=[0.7], random_state=0
    )
    frame = pd.DataFrame(X.astype("float32"), columns=[f"f{i}" for i in range(8)])
    rng = np.random.default_rng(0)
    frame["proto"] = rng.choice(["tcp", "udp", "icmp"], size=len(frame))
    frame["label"] = y.astype("int8")
    kinds = rng.choice(["DoS", "Probe"], size=len(frame))
    frame["attack_type"] = np.where(y == 0, "BENIGN", kinds)
    return frame


def test_select_best_prefers_lowest_fpr_meeting_recall() -> None:
    def row(model: str, recall: float, fpr: float, f1: float = 0.9) -> dict:
        return {"model": model, "operating_point": "recall_target", "split": "val",
                "recall": recall, "fpr": fpr, "f1": f1}

    rows = [row("a", 0.96, 0.05), row("b", 0.95, 0.01), row("c", 0.90, 0.001)]
    assert train.select_best(rows, 0.95) == "b"
    assert train.select_best([row("a", 0.9, 0.2), row("b", 0.92, 0.3)], 0.95) == "b"


def test_soft_voting_averages_member_probabilities() -> None:
    class Fixed:
        def __init__(self, p: float) -> None:
            self.p = p

        def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
            return np.column_stack([np.full(len(X), 1 - self.p), np.full(len(X), self.p)])

    ensemble = SoftVotingEnsemble([Fixed(0.2), Fixed(0.6)])
    X = pd.DataFrame({"a": [1, 2, 3]})
    assert attack_scores(ensemble, X) == pytest.approx([0.4, 0.4, 0.4])
    assert ensemble.predict(X, threshold=0.4).tolist() == [1, 1, 1]


def test_end_to_end_train_evaluate_predict(
    tiny_dataset: pd.DataFrame, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config, "MODELS_DIR", tmp_path / "models")
    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(train, "load_processed", lambda key: tiny_dataset)

    best = train.run("unsw_nb15", n_iter=2, tune_sample=600, cv_folds=3)

    dataset = config.get_dataset("unsw_nb15")
    metrics = pd.read_csv(dataset.reports_dir / "metrics.csv")
    assert set(metrics["model"]) == set(evaluate.MODEL_ORDER)
    assert set(metrics["operating_point"]) == set(train.OPERATING_POINTS)
    val = metrics[metrics["split"] == "val"]
    at_target = val[val["operating_point"] == "recall_target"]
    assert (at_target["recall"] >= config.RECALL_TARGET).all()
    at_budget = val[val["operating_point"] == "fpr_budget"]
    assert (at_budget["fpr"] <= config.FPR_TARGET).all()
    summary = json.loads((dataset.reports_dir / "training_summary.json").read_text())
    assert summary["best_model"] == best

    evaluate.run("unsw_nb15")
    assert (dataset.reports_dir / "resultados.md").is_file()
    assert (dataset.reports_dir / "figures" / "roc.png").is_file()

    bundle = predict.load_bundle("unsw_nb15")
    splits = make_splits(tiny_dataset)
    scores = attack_scores(bundle["model"], splits.test.X)
    for point in train.OPERATING_POINTS:
        result = predict.classify(splits.test.X, bundle, point)
        assert set(result["classification"]) <= {predict.NORMAL_TEXT, predict.ATTACK_TEXT}
        expected = scores >= bundle["thresholds"][point]
        assert (result["prediction"].to_numpy() == expected.astype(int)).all()
    assert bundle["threshold"] == bundle["thresholds"]["recall_target"]

    # Rescoring from saved scores reproduces the stored metrics without retraining.
    before = pd.read_csv(dataset.reports_dir / "metrics.csv")
    assert train.rescore("unsw_nb15") == best
    pd.testing.assert_frame_equal(before, pd.read_csv(dataset.reports_dir / "metrics.csv"))


def test_predict_rejects_missing_columns_and_bad_values() -> None:
    bundle = {
        "feature_columns": ["a", "b"],
        "numeric_columns": ["a", "b"],
        "categorical_columns": [],
        "model": None,
        "thresholds": {"recall_target": 0.5},
    }
    with pytest.raises(ValueError, match="missing"):
        predict.prepare_features(pd.DataFrame({"a": [1.0]}), bundle)
    with pytest.raises(ValueError, match="infinite"):
        predict.prepare_features(pd.DataFrame({" a": [np.inf], "b ": [1.0]}), bundle)
