from __future__ import annotations

import pandas as pd
import pytest

from src import config
from src.data_loader import (
    load_processed,
    make_splits,
    split_features_target,
    stratified_subsample,
)
from src.utils.scaling import build_scaler


def test_split_sizes_and_no_overlap(processed_frame: pd.DataFrame) -> None:
    splits = make_splits(processed_frame)
    total = len(processed_frame)

    assert len(splits.train) + len(splits.val) + len(splits.test) == total
    assert abs(len(splits.test) / total - config.TEST_SIZE) < 0.02
    assert abs(len(splits.val) / total - config.VAL_SIZE) < 0.02
    indexes = [set(p.X.index) for p in (splits.train, splits.val, splits.test)]
    assert indexes[0].isdisjoint(indexes[1])
    assert indexes[0].isdisjoint(indexes[2])
    assert indexes[1].isdisjoint(indexes[2])
    assert splits.feature_names == list("wxyz")


def test_split_is_stratified_by_attack_type(processed_frame: pd.DataFrame) -> None:
    splits = make_splits(processed_frame)

    for partition in (splits.train, splits.val, splits.test):
        assert set(partition.attack) == {"BENIGN", "DoS Hulk", "Rare"}
    full = processed_frame["attack_type"].value_counts(normalize=True)
    train = splits.train.attack.value_counts(normalize=True)
    for name in full.index:
        assert abs(full[name] - train[name]) < 0.03


def test_split_is_deterministic(processed_frame: pd.DataFrame) -> None:
    first = make_splits(processed_frame)
    second = make_splits(processed_frame)
    pd.testing.assert_frame_equal(first.train.X, second.train.X)
    pd.testing.assert_series_equal(first.test.y, second.test.y)


def test_split_features_target_excludes_targets(processed_frame: pd.DataFrame) -> None:
    X, y, attack = split_features_target(processed_frame)
    assert config.LABEL_COLUMN not in X.columns
    assert config.ATTACK_TYPE_COLUMN not in X.columns
    assert len(X) == len(y) == len(attack)


def test_stratified_subsample_keeps_proportions(processed_frame: pd.DataFrame) -> None:
    X, y, attack = split_features_target(processed_frame)
    X_sub, y_sub = stratified_subsample(X, y, 100, stratify=attack)
    assert len(X_sub) == len(y_sub) == 100
    assert abs(y_sub.mean() - y.mean()) < 0.05
    X_all, _ = stratified_subsample(X, y, 10_000)
    assert len(X_all) == len(X)


def test_load_processed_missing_file_has_helpful_message(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="src.preprocess"):
        load_processed(path=tmp_path / "missing.parquet")


def test_get_dataset_rejects_unknown_key() -> None:
    assert config.get_dataset("unsw_nb15").categorical_columns == ("proto", "service", "state")
    with pytest.raises(ValueError, match="Unknown dataset"):
        config.get_dataset("nsl_kdd")


def test_scaler_factory() -> None:
    assert build_scaler("standard").__class__.__name__ == "StandardScaler"
    assert build_scaler("minmax").__class__.__name__ == "MinMaxScaler"
    with pytest.raises(ValueError):
        build_scaler("robust")  # type: ignore[arg-type]
