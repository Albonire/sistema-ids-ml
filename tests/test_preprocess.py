from __future__ import annotations

import numpy as np
import pandas as pd

from src import config
from src.preprocess import clean, normalize_labels


def test_normalize_labels_fixes_non_ascii_dash_and_spaces() -> None:
    raw = pd.Series(["  BENIGN ", "Web Attack \x96 Brute Force", "Web Attack - XSS", "DoS  Hulk"])
    result = normalize_labels(raw).tolist()
    assert result == ["BENIGN", "Web Attack - Brute Force", "Web Attack - XSS", "DoS Hulk"]


def test_clean_removes_bad_rows_and_columns(raw_frame: pd.DataFrame) -> None:
    cleaned, report = clean(raw_frame)

    assert report.rows_raw == 10
    assert report.rows_with_infinite == 1
    assert report.rows_with_nan == 2  # the infinity becomes NaN, plus the real NaN
    assert report.rows_removed_missing == 2
    assert report.rows_removed_duplicates == 1
    assert report.rows_removed_conflicting == 2
    assert report.rows_final == 5 == len(cleaned)
    assert report.duplicated_header_dropped == ["a.1"]
    assert report.constant_columns_dropped == ["const"]
    assert report.negative_value_counts == {"c": 1}
    assert not np.isinf(cleaned.select_dtypes("number").to_numpy()).any()
    assert not cleaned.isna().any().any()


def test_clean_builds_targets_and_dtypes(raw_frame: pd.DataFrame) -> None:
    cleaned, _ = clean(raw_frame)

    assert set(cleaned.columns) == {"a", "b", "c", config.LABEL_COLUMN, config.ATTACK_TYPE_COLUMN}
    assert cleaned[config.LABEL_COLUMN].dtype == np.int8
    assert cleaned["a"].dtype == np.float32
    mapping = dict(zip(cleaned[config.ATTACK_TYPE_COLUMN], cleaned[config.LABEL_COLUMN]))
    assert mapping["BENIGN"] == 0
    assert mapping["DoS Hulk"] == 1
    assert mapping["Web Attack - Brute Force"] == 1


def test_clean_does_not_mutate_input(raw_frame: pd.DataFrame) -> None:
    snapshot = raw_frame.copy()
    clean(raw_frame)
    pd.testing.assert_frame_equal(raw_frame, snapshot)
