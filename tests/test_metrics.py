from __future__ import annotations

import numpy as np
import pytest

from src.metrics import (
    bootstrap_intervals,
    compute_metrics,
    select_threshold,
    select_threshold_for_fpr,
)


def test_compute_metrics_matches_hand_calculation() -> None:
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    scores = np.array([0.9, 0.8, 0.7, 0.2, 0.6, 0.1, 0.1, 0.2, 0.3, 0.4])
    m = compute_metrics(y, scores, threshold=0.5)
    assert (m.tp, m.fn, m.fp, m.tn) == (3, 1, 1, 5)
    assert m.recall == pytest.approx(3 / 4)
    assert m.precision == pytest.approx(3 / 4)
    assert m.fpr == pytest.approx(1 / 6)
    assert m.accuracy == pytest.approx(8 / 10)
    assert m.f1 == pytest.approx(0.75)


def test_compute_metrics_handles_single_class_without_crashing() -> None:
    m = compute_metrics(np.zeros(5), np.linspace(0, 1, 5), threshold=0.5)
    assert m.recall == 0.0
    assert np.isnan(m.roc_auc)


def test_select_threshold_minimises_fpr_under_recall_constraint() -> None:
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0])
    scores = np.array([0.95, 0.9, 0.6, 0.4, 0.5, 0.3, 0.2, 0.1])
    threshold = select_threshold(y, scores, recall_target=0.75)
    m = compute_metrics(y, scores, threshold)
    assert m.recall >= 0.75
    assert m.fp == 0  # recall 0.75 is reachable at threshold 0.6 without any false alarm
    assert threshold == pytest.approx(0.6)


def test_select_threshold_never_splits_tied_scores() -> None:
    y = np.array([1, 1, 0, 0])
    scores = np.array([0.5, 0.5, 0.5, 0.5])
    threshold = select_threshold(y, scores, recall_target=1.0)
    assert compute_metrics(y, scores, threshold).recall == 1.0


def test_select_threshold_falls_back_to_max_recall_when_unreachable() -> None:
    y = np.array([1, 1, 0, 0])
    scores = np.array([0.9, 0.1, 0.8, 0.2])
    threshold = select_threshold(y, scores, recall_target=1.01)
    assert compute_metrics(y, scores, threshold).recall == 1.0


def test_select_threshold_single_class_returns_default() -> None:
    assert select_threshold(np.ones(4), np.array([0.1, 0.2, 0.3, 0.4]), 0.95) == 0.5


def test_bootstrap_interval_brackets_point_estimate_and_shrinks_with_n() -> None:
    rng = np.random.default_rng(0)

    def metrics_for(n: int):
        y = (rng.random(n) < 0.4).astype(int)
        scores = np.clip(y * 0.6 + rng.normal(0.2, 0.25, n), 0, 1)
        return compute_metrics(y, scores, 0.5)

    small, large = metrics_for(500), metrics_for(50_000)
    for m in (small, large):
        low, high = bootstrap_intervals(m)["fpr"]
        assert low <= m.fpr <= high
    width = lambda m: np.subtract(*bootstrap_intervals(m)["fpr"][::-1])
    assert width(large) < width(small)


def test_select_threshold_for_fpr_maximises_recall_within_budget() -> None:
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    scores = np.array([0.95, 0.9, 0.55, 0.3, 0.6, 0.5, 0.2, 0.1, 0.05, 0.01])
    threshold = select_threshold_for_fpr(y, scores, fpr_budget=1 / 6)
    m = compute_metrics(y, scores, threshold)
    assert m.fpr <= 1 / 6
    assert m.recall == pytest.approx(0.75)  # one false alarm (0.6) buys the 0.55 attack
    strict = compute_metrics(y, scores, select_threshold_for_fpr(y, scores, fpr_budget=0.0))
    assert strict.fp == 0 and strict.recall == pytest.approx(0.5)


def test_select_threshold_for_fpr_with_unreachable_budget_flags_nothing() -> None:
    y = np.array([1, 0])
    scores = np.array([0.5, 0.5])  # tied: any cut flags the negative too
    threshold = select_threshold_for_fpr(y, scores, fpr_budget=0.0)
    assert compute_metrics(y, scores, threshold).tp == 0
    assert select_threshold_for_fpr(np.ones(3), np.array([0.1, 0.2, 0.3]), 0.02) == 0.5
