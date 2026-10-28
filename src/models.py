"""Model factories: literature-style baselines and improved pipelines.

Baseline hyperparameters follow Entregable 1, section 8.4 (Random Forest with
n_estimators=100; XGBoost with n_estimators=100 and max_depth=5). The improved
variants add correlation-based feature filtering (fitted on train only) and
hyperparameters selected by 5-fold cross validation; the decision threshold is
calibrated separately on the validation split (see `src.metrics`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src import config
from src.features import CorrelationFilter, build_preprocessor

Algorithm = Literal["rf", "xgb"]

ALGORITHM_LABELS: dict[str, str] = {"rf": "Random Forest", "xgb": "XGBoost", "mix": "Mix (RF + XGB)"}

RF_SEARCH_SPACE: dict[str, list[Any]] = {
    "clf__n_estimators": [100, 200, 300],
    "clf__max_depth": [None, 12, 20, 30],
    "clf__min_samples_leaf": [1, 2, 4],
    "clf__max_features": ["sqrt", 0.3],
}

XGB_SEARCH_SPACE: dict[str, list[Any]] = {
    "clf__n_estimators": [200, 400, 600],
    "clf__max_depth": [4, 6, 8, 10],
    "clf__learning_rate": [0.05, 0.1, 0.2],
    "clf__subsample": [0.7, 0.85, 1.0],
    "clf__colsample_bytree": [0.6, 0.8, 1.0],
    "clf__min_child_weight": [1, 3, 5],
}


def _classifier(algorithm: Algorithm) -> Any:
    if algorithm == "rf":
        return RandomForestClassifier(
            n_estimators=100, random_state=config.RANDOM_STATE, n_jobs=-1
        )
    return XGBClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=config.RANDOM_STATE,
        n_jobs=-1,
        tree_method="hist",
        eval_metric="logloss",
    )


def build_pipeline(
    algorithm: Algorithm,
    numeric_columns: list[str],
    categorical_columns: list[str],
    improved: bool,
) -> Pipeline:
    """Build an unfitted pipeline: encoding, optional correlation filter, classifier."""
    steps: list[tuple[str, Any]] = [
        ("prep", build_preprocessor(numeric_columns, categorical_columns))
    ]
    if improved:
        steps.append(("filter", CorrelationFilter()))
    steps.append(("clf", _classifier(algorithm)))
    return Pipeline(steps)


def search_space(algorithm: Algorithm) -> dict[str, list[Any]]:
    return RF_SEARCH_SPACE if algorithm == "rf" else XGB_SEARCH_SPACE


def attack_scores(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Probability of the attack class for every row."""
    return np.asarray(model.predict_proba(X))[:, 1]


@dataclass
class SoftVotingEnsemble:
    """Average the attack probabilities of already fitted pipelines (the "mix")."""

    members: list[Any]

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        attack = np.mean([attack_scores(member, X) for member in self.members], axis=0)
        return np.column_stack([1.0 - attack, attack])

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        return (attack_scores(self, X) >= threshold).astype(int)
