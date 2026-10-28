from __future__ import annotations

import numpy as np
import pandas as pd

from src.leakage_ablation import evaluate_protocol, leaked_share


def test_leaked_share_counts_exact_feature_matches() -> None:
    train = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [1.0, 2.0, 3.0]})
    test = pd.DataFrame({"a": [1.0, 9.0, 3.0, 8.0], "b": [1.0, 9.0, 3.0, 8.0]})
    assert leaked_share(train, test) == 0.5


def test_evaluate_protocol_reports_metrics_for_a_processed_frame() -> None:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(rng.normal(size=(600, 4)).astype("float32"), columns=list("wxyz"))
    frame["label"] = (frame["w"] + frame["x"] > 0).astype("int8")
    frame["attack_type"] = np.where(frame["label"] == 0, "BENIGN", "Attack")
    result = evaluate_protocol(frame)
    assert result["rows"] == 600
    assert 0.8 < result["accuracy"] <= 1.0
    assert result["leaked_test_share"] == 0.0
