"""Shared synthetic fixtures reproducing the quirks of the raw CICIDS2017 files."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def raw_frame() -> pd.DataFrame:
    """Small raw-like frame with infinities, NaN, duplicates, conflicts and a constant column."""
    rows = [
        # a, b, c, const, dup_header, label
        [1.0, 10.0, 5.0, 0.0, 1.0, "BENIGN"],
        [2.0, 20.0, 6.0, 0.0, 2.0, "BENIGN"],
        [2.0, 20.0, 6.0, 0.0, 2.0, "BENIGN"],  # exact duplicate
        [3.0, np.inf, 7.0, 0.0, 3.0, "BENIGN"],  # infinite value
        [4.0, 40.0, np.nan, 0.0, 4.0, "BENIGN"],  # missing value
        [5.0, 50.0, 8.0, 0.0, 5.0, "DoS Hulk"],
        [9.0, 90.0, 9.0, 0.0, 9.0, "BENIGN"],  # conflicting pair (same features)
        [9.0, 90.0, 9.0, 0.0, 9.0, "PortScan"],
        [6.0, 60.0, -1.0, 0.0, 6.0, "Web Attack \x96 Brute Force"],
        [7.0, 70.0, 3.0, 0.0, 7.0, "  BENIGN "],
    ]
    return pd.DataFrame(rows, columns=["a", "b", "c", "const", "a.1", "Label"])


@pytest.fixture
def processed_frame() -> pd.DataFrame:
    """Synthetic processed dataset with three attack types and a rare class."""
    rng = np.random.default_rng(0)
    sizes = {"BENIGN": 400, "DoS Hulk": 100, "Rare": 10}
    parts = []
    for name, size in sizes.items():
        frame = pd.DataFrame(rng.normal(size=(size, 4)).astype("float32"), columns=list("wxyz"))
        frame["label"] = np.int8(0 if name == "BENIGN" else 1)
        frame["attack_type"] = name
        parts.append(frame)
    return pd.concat(parts, ignore_index=True)
