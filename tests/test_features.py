from __future__ import annotations

import numpy as np
import pandas as pd

from src.features import CorrelationFilter, build_preprocessor, split_column_types


def test_correlation_filter_drops_later_duplicate_columns() -> None:
    rng = np.random.default_rng(0)
    a = rng.normal(size=200)
    frame = pd.DataFrame({"a": a, "a_copy": a * 3 + 1, "b": rng.normal(size=200), "c": rng.normal(size=200)})
    selector = CorrelationFilter(threshold=0.95).fit(frame)
    assert selector.get_feature_names_out(list(frame.columns)).tolist() == ["a", "b", "c"]
    assert selector.transform(frame).shape == (200, 3)


def test_correlation_filter_uses_only_fit_data() -> None:
    rng = np.random.default_rng(1)
    train = pd.DataFrame({"x": rng.normal(size=100), "y": rng.normal(size=100)})
    selector = CorrelationFilter().fit(train)
    test = pd.DataFrame({"x": np.arange(5.0), "y": np.arange(5.0)})  # perfectly correlated here
    assert selector.transform(test).shape == (5, 2)


def test_correlation_filter_tolerates_constant_columns() -> None:
    frame = pd.DataFrame({"const": np.ones(50), "v": np.arange(50.0)})
    assert CorrelationFilter().fit(frame).transform(frame).shape == (50, 2)


def test_preprocessor_encodes_categoricals_and_handles_unseen_values() -> None:
    train = pd.DataFrame({"n": [1.0, 2.0, 3.0, 4.0] * 50, "proto": ["tcp", "udp", "tcp", "icmp"] * 50})
    prep = build_preprocessor(["n"], ["proto"]).fit(train)
    out = prep.transform(pd.DataFrame({"n": [1.0], "proto": ["never-seen"]}))
    assert out.shape[0] == 1
    assert "n" in out.columns
    assert out.select_dtypes(exclude="number").empty


def test_split_column_types() -> None:
    frame = pd.DataFrame({"n": [1.0, 2.0], "s": ["a", "b"]})
    assert split_column_types(frame) == (["n"], ["s"])
