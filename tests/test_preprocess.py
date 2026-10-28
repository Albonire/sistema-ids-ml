from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import config
from src.preprocess import clean, normalize_labels, normalize_unsw


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


def _unsw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "dur": [0.1, 0.2, 0.2, np.inf, 0.5],
            "proto": ["tcp", " udp", "udp", "tcp", "tcp"],
            "service": ["-", "dns", "dns", "http", "http"],
            "spkts": [1, 2, 2, 3, 4],
            "attack_cat": ["Normal", "Generic", "Generic", "Normal", "Exploits"],
            "label": [0, 1, 1, 0, 1],
        }
    )


def test_normalize_unsw_maps_labels_and_drops_ids() -> None:
    frame = normalize_unsw(_unsw_frame())
    assert "id" not in frame.columns and "label" not in frame.columns
    assert frame["Label"].tolist() == ["BENIGN", "Generic", "Generic", "BENIGN", "Exploits"]


def test_normalize_unsw_rejects_inconsistent_labels() -> None:
    broken = _unsw_frame()
    broken.loc[0, "label"] = 1
    with pytest.raises(ValueError, match="disagrees"):
        normalize_unsw(broken)


def test_clean_keeps_categorical_columns_as_strings() -> None:
    cleaned, report = clean(
        normalize_unsw(_unsw_frame()), categorical_columns=("proto", "service"), dataset="unsw_nb15"
    )
    assert report.dataset == "unsw_nb15"
    assert report.rows_removed_missing == 1  # the infinite duration
    assert report.rows_removed_duplicates == 1  # the repeated Generic flow
    assert set(cleaned["proto"]) <= {"tcp", "udp"}
    assert cleaned["dur"].dtype == np.float32
    assert not pd.api.types.is_numeric_dtype(cleaned["proto"])


def test_clean_treats_same_vector_with_two_attack_families_as_duplicate_not_conflict() -> None:
    frame = pd.DataFrame(
        {
            "a": [1.0, 1.0, 2.0, 2.0],
            "b": [5.0, 5.0, 6.0, 6.0],
            "Label": ["DoS Hulk", "DoS GoldenEye", "BENIGN", "PortScan"],
        }
    )
    cleaned, report = clean(frame)
    assert report.rows_removed_duplicates == 1  # the two attack families collapse to one row
    assert report.rows_removed_conflicting == 2  # normal vs attack is a true conflict
    assert cleaned["attack_type"].tolist() == ["DoS Hulk"]
    assert cleaned["label"].tolist() == [1]


def test_clean_deduplicates_after_float32_rounding() -> None:
    frame = pd.DataFrame(
        {"a": [1.0, 1.0 + 1e-12, 2.0], "b": [5.0, 5.0, 6.0], "Label": ["BENIGN", "BENIGN", "DoS Hulk"]}
    )
    cleaned, report = clean(frame)
    assert report.rows_removed_duplicates == 1
    assert len(cleaned) == 2
