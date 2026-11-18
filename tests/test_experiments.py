from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification

from src import experiments
from src.metrics import compute_metrics, paired_bootstrap_difference


@pytest.fixture
def tiny_frame() -> pd.DataFrame:
    X, y = make_classification(
        n_samples=900, n_features=6, n_informative=4, n_redundant=1, weights=[0.7], random_state=1
    )
    frame = pd.DataFrame(X.astype("float32"), columns=[f"f{i}" for i in range(6)])
    rng = np.random.default_rng(1)
    frame["proto"] = rng.choice(["tcp", "udp"], size=len(frame))
    frame["label"] = y.astype("int8")
    frame["attack_type"] = np.where(y == 0, "BENIGN", rng.choice(["DoS", "Probe"], size=len(frame)))
    return frame


def _scores(n: int, shift: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.4).astype(int)
    return y, np.clip(y * shift + rng.normal(0.2, 0.25, n), 0, 1)


def test_paired_bootstrap_matches_direct_difference_and_flags_a_real_gap() -> None:
    y, better = _scores(20_000, 0.55, 0)
    _, worse = _scores(20_000, 0.30, 0)
    result = paired_bootstrap_difference(y, better, 0.5, worse, 0.5)
    direct = compute_metrics(y, better, 0.5).recall - compute_metrics(y, worse, 0.5).recall
    assert result["recall"]["difference"] == pytest.approx(direct)
    assert result["recall"]["low"] <= direct <= result["recall"]["high"]
    assert result["recall"]["p_value"] < 0.01


def test_paired_bootstrap_of_identical_models_is_null() -> None:
    y, scores = _scores(5_000, 0.5, 1)
    result = paired_bootstrap_difference(y, scores, 0.5, scores, 0.5)
    assert result["fpr"] == {"difference": 0.0, "low": 0.0, "high": 0.0, "p_value": 1.0}


def test_paired_bootstrap_interval_shrinks_with_more_rows() -> None:
    def width(n: int) -> float:
        y, a = _scores(n, 0.5, 2)
        _, b = _scores(n, 0.45, 3)
        r = paired_bootstrap_difference(y, a, 0.5, b, 0.5)["recall"]
        return r["high"] - r["low"]

    assert width(40_000) < width(1_000)


def test_split_official_partitions_assigns_by_size_not_by_order() -> None:
    small, large = pd.DataFrame({"a": range(3)}), pd.DataFrame({"a": range(10)})
    train, test = experiments.split_official_partitions([small, large])
    assert len(train) == 10 and len(test) == 3
    with pytest.raises(ValueError):
        experiments.split_official_partitions([small])


def test_seen_mask_flags_exact_vectors_including_categoricals() -> None:
    train = pd.DataFrame({"a": [1.0, 2.0], "c": ["x", "y"]})
    test = pd.DataFrame({"a": [1.0, 2.0, 3.0], "c": ["x", "z", "x"]})
    assert experiments.seen_mask(train, test).tolist() == [True, False, False]


def test_drop_feature_group_is_strict() -> None:
    X = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    assert list(experiments.drop_feature_group(X, ["a", "c"]).columns) == ["b"]
    with pytest.raises(KeyError):
        experiments.drop_feature_group(X, ["typo"])


def test_feature_groups_only_name_columns_of_their_dataset() -> None:
    assert set(experiments.FEATURE_GROUPS) == {"unsw_nb15", "cicids2017"}
    for groups in experiments.FEATURE_GROUPS.values():
        assert groups["completo"] == []


def test_seed_rows_are_deterministic_and_seed_dependent(tiny_frame: pd.DataFrame) -> None:
    params = {"rf": {"clf__n_estimators": 20}, "xgb": {"clf__n_estimators": 20}}
    first = pd.DataFrame(experiments.seed_rows(tiny_frame, 3, params))
    again = pd.DataFrame(experiments.seed_rows(tiny_frame, 3, params))
    other = pd.DataFrame(experiments.seed_rows(tiny_frame, 4, params))
    pd.testing.assert_frame_equal(first, again)
    assert set(first["model"]) == {
        "rf_baseline", "rf_improved", "xgb_baseline", "xgb_improved", "mix_baseline", "mix_improved"
    }
    assert not np.allclose(first["recall"], other["recall"])


def test_summarize_seeds_and_best_by_seed(tiny_frame: pd.DataFrame) -> None:
    params = {"rf": {"clf__n_estimators": 20}, "xgb": {"clf__n_estimators": 20}}
    rows = pd.concat(
        [pd.DataFrame(experiments.seed_rows(tiny_frame, s, params)) for s in (1, 2)],
        ignore_index=True,
    )
    summary = experiments.summarize_seeds(rows)
    assert (summary["n_seeds"] == 2).all()
    assert len(summary) == 6 * 3
    assert {"recall_mean", "recall_std", "fpr_max"} <= set(summary.columns)
    wins = experiments.best_by_seed(rows)
    assert set(wins) == {"1", "2"} and set(wins["1"]) == {"recall_target", "fpr_budget"}


def test_ablation_rows_drop_exactly_the_named_columns(tiny_frame: pd.DataFrame) -> None:
    groups = {"completo": [], "sin f0 y proto": ["f0", "proto"]}
    rows = experiments.ablation_rows(tiny_frame, groups, {"clf__n_estimators": 20})
    assert {r["group"] for r in rows} == set(groups)
    assert {r["operating_point"] for r in rows} == {"default", "recall_target", "fpr_budget"}
    dropped = {r["group"]: r["dropped"] for r in rows}
    assert dropped["completo"] == "" and dropped["sin f0 y proto"] == "f0; proto"


def test_run_seeds_resumes_from_the_partial_file(
    tiny_frame: pd.DataFrame, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A seed stored in the partial file is reused instead of being fitted again."""
    from src import config

    monkeypatch.setattr(config, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(experiments, "load_processed", lambda key: tiny_frame)
    dataset = config.get_dataset("unsw_nb15")
    dataset.reports_dir.mkdir(parents=True)
    params = {"rf": {"clf__n_estimators": 20}, "xgb": {"clf__n_estimators": 20}}
    stored = pd.DataFrame(experiments.seed_rows(tiny_frame, config.RANDOM_STATE, params))
    stored.insert(0, "dataset", "unsw_nb15")
    stored.drop(columns="seed").to_csv(dataset.reports_dir / "metrics.csv", index=False)
    summary = {"models": {f"{a}_improved": {"best_params": params[a]} for a in ("rf", "xgb")}}
    (dataset.reports_dir / "training_summary.json").write_text(__import__("json").dumps(summary))
    pd.DataFrame(experiments.seed_rows(tiny_frame, 1, params)).to_csv(
        dataset.reports_dir / "multiseed.partial.csv", index=False
    )

    calls: list[int] = []
    real = experiments.seed_rows
    monkeypatch.setattr(experiments, "seed_rows", lambda df, seed, p: calls.append(seed) or real(df, seed, p))
    rows = experiments.run_seeds("unsw_nb15", seeds=(config.RANDOM_STATE, 1, 2))

    assert calls == [2]  # seed 1 came from the partial file, seed 42 from metrics.csv
    assert set(rows["seed"]) == {config.RANDOM_STATE, 1, 2}
    assert not (dataset.reports_dir / "multiseed.partial.csv").exists()
