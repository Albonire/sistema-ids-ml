"""Evaluation metrics and decision threshold selection for the IDS."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


@dataclass(frozen=True)
class Metrics:
    """Binary classification metrics, with attack as the positive class."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    fpr: float
    roc_auc: float
    pr_auc: float
    tp: int
    tn: int
    fp: int
    fn: int
    threshold: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator > 0 else 0.0


def compute_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float = 0.5) -> Metrics:
    """Compute AGENT.md metrics from attack scores and a decision threshold."""
    y = np.asarray(y_true).astype(int)
    predicted = (np.asarray(scores) >= threshold).astype(int)
    tp = int(((predicted == 1) & (y == 1)).sum())
    tn = int(((predicted == 0) & (y == 0)).sum())
    fp = int(((predicted == 1) & (y == 0)).sum())
    fn = int(((predicted == 0) & (y == 1)).sum())
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    both_classes = len(np.unique(y)) == 2
    return Metrics(
        accuracy=_safe_divide(tp + tn, len(y)),
        precision=precision,
        recall=recall,
        f1=_safe_divide(2 * precision * recall, precision + recall),
        fpr=_safe_divide(fp, fp + tn),
        roc_auc=float(roc_auc_score(y, scores)) if both_classes else float("nan"),
        pr_auc=float(average_precision_score(y, scores)) if both_classes else float("nan"),
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        threshold=float(threshold),
    )


def select_threshold(y_true: np.ndarray, scores: np.ndarray, recall_target: float) -> float:
    """Pick the decision threshold that minimises FPR while keeping Recall >= target.

    Among thresholds meeting the recall target the one with the lowest FPR wins; ties go
    to the highest threshold (fewest alerts). If the target is unreachable the threshold
    with the highest recall is returned. Candidate thresholds are the observed scores.
    """
    y = np.asarray(y_true).astype(int)
    s = np.asarray(scores, dtype=float)
    positives = int((y == 1).sum())
    negatives = int((y == 0).sum())
    if positives == 0 or negatives == 0:
        return 0.5

    order = np.argsort(-s, kind="stable")
    sorted_scores = s[order]
    sorted_y = y[order]
    tp_cum = np.cumsum(sorted_y)
    fp_cum = np.cumsum(1 - sorted_y)
    # Only evaluate cut points where the score changes, so equal scores are never split.
    last_of_run = np.r_[sorted_scores[1:] != sorted_scores[:-1], True]
    recall = tp_cum[last_of_run] / positives
    fpr = fp_cum[last_of_run] / negatives
    thresholds = sorted_scores[last_of_run]

    feasible = recall >= recall_target
    if not feasible.any():
        return float(thresholds[int(np.argmax(recall))])
    candidate_fpr = np.where(feasible, fpr, np.inf)
    best = int(np.flatnonzero(candidate_fpr == candidate_fpr.min())[0])
    return float(thresholds[best])


def select_threshold_for_fpr(y_true: np.ndarray, scores: np.ndarray, fpr_budget: float) -> float:
    """Pick the decision threshold that maximises recall while keeping FPR <= budget.

    Complements `select_threshold`: it models an analyst team with a fixed false alarm
    budget. Ties go to the highest threshold. If even the strictest cut exceeds the budget
    (only possible with tied scores), a threshold above every score is returned so that
    nothing is flagged.
    """
    y = np.asarray(y_true).astype(int)
    s = np.asarray(scores, dtype=float)
    positives = int((y == 1).sum())
    negatives = int((y == 0).sum())
    if positives == 0 or negatives == 0:
        return 0.5

    order = np.argsort(-s, kind="stable")
    sorted_scores = s[order]
    sorted_y = y[order]
    tp_cum = np.cumsum(sorted_y)
    fp_cum = np.cumsum(1 - sorted_y)
    last_of_run = np.r_[sorted_scores[1:] != sorted_scores[:-1], True]
    recall = tp_cum[last_of_run] / positives
    fpr = fp_cum[last_of_run] / negatives
    thresholds = sorted_scores[last_of_run]

    feasible = fpr <= fpr_budget
    if not feasible.any():
        return float(np.nextafter(sorted_scores[0], np.inf))
    candidate_recall = np.where(feasible, recall, -1.0)
    return float(thresholds[int(np.argmax(candidate_recall))])


def bootstrap_intervals(
    metrics: Metrics, n_boot: int = 2000, seed: int = 42, level: float = 0.95
) -> dict[str, tuple[float, float]]:
    """Bootstrap confidence intervals for recall, FPR and precision from confusion counts.

    Resampling n rows with replacement makes the four confusion cells follow a multinomial
    distribution, so the exact bootstrap needs no row-level resampling. The interval
    captures test-sampling noise only, not variation due to training randomness.
    """
    counts = np.array([metrics.tp, metrics.fn, metrics.fp, metrics.tn], dtype=float)
    total = int(counts.sum())
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(total, counts / total, size=n_boot).astype(float)
    tp, fn, fp, tn = draws.T
    with np.errstate(divide="ignore", invalid="ignore"):
        samples = {
            "recall": np.nan_to_num(tp / (tp + fn)),
            "fpr": np.nan_to_num(fp / (fp + tn)),
            "precision": np.nan_to_num(tp / (tp + fp)),
        }
    alpha = (1.0 - level) / 2.0
    return {
        name: (float(np.quantile(values, alpha)), float(np.quantile(values, 1.0 - alpha)))
        for name, values in samples.items()
    }
