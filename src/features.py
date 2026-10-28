"""Feature engineering building blocks that must be fitted on the training split only."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder

CORRELATION_THRESHOLD = 0.95


class CorrelationFilter(BaseEstimator, TransformerMixin):
    """Drop one feature of every pair whose absolute Pearson correlation exceeds a threshold.

    Features are visited in column order and a column is dropped when it correlates above
    the threshold with a column that was already kept, so the choice is deterministic.
    Fitted on training data only, so no test information leaks into the selection.
    """

    def __init__(self, threshold: float = CORRELATION_THRESHOLD) -> None:
        self.threshold = threshold

    def fit(self, X: pd.DataFrame | np.ndarray, y: object = None) -> CorrelationFilter:
        frame = pd.DataFrame(X)
        corr = frame.corr().abs().to_numpy()
        corr = np.nan_to_num(corr, nan=0.0)
        keep: list[int] = []
        for column in range(corr.shape[0]):
            if all(corr[column, kept] <= self.threshold for kept in keep):
                keep.append(column)
        self.n_features_in_ = corr.shape[0]
        self.keep_indices_ = np.array(keep, dtype=int)
        self.dropped_indices_ = np.setdiff1d(np.arange(corr.shape[0]), self.keep_indices_)
        return self

    def transform(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        values = X.to_numpy() if isinstance(X, pd.DataFrame) else np.asarray(X)
        return values[:, self.keep_indices_]

    def get_feature_names_out(self, input_features: list[str] | None = None) -> np.ndarray:
        if input_features is None:
            input_features = [f"x{i}" for i in range(self.n_features_in_)]
        return np.asarray(input_features, dtype=object)[self.keep_indices_]


def build_preprocessor(
    numeric_columns: list[str], categorical_columns: list[str]
) -> ColumnTransformer:
    """Pass numeric columns through and one-hot encode categoricals.

    Tree ensembles do not need scaling. Rare or unseen categories map to an
    "infrequent" bucket so inference on new flows never fails.
    """
    transformers: list[tuple[str, object, list[str]]] = [("num", "passthrough", numeric_columns)]
    if categorical_columns:
        encoder = OneHotEncoder(
            handle_unknown="infrequent_if_exist",
            min_frequency=0.01,
            sparse_output=False,
            dtype=np.float32,
        )
        transformers.append(("cat", encoder, categorical_columns))
    return ColumnTransformer(transformers, verbose_feature_names_out=False).set_output(
        transform="pandas"
    )


def split_column_types(X: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Return (numeric, categorical) column names of a feature frame."""
    numeric = [c for c in X.columns if pd.api.types.is_numeric_dtype(X[c])]
    categorical = [c for c in X.columns if c not in numeric]
    return numeric, categorical
