"""Deterministic loading and splitting of the processed CICIDS2017 dataset."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src import config


@dataclass(frozen=True)
class DataSplit:
    """Train/test partition with binary targets and the multiclass attack type."""

    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    attack_train: pd.Series
    attack_test: pd.Series

    @property
    def feature_names(self) -> list[str]:
        return list(self.X_train.columns)


def load_processed(path: Path = config.PROCESSED_FILE) -> pd.DataFrame:
    """Load the cleaned dataset produced by `python -m src.preprocess`."""
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.download_data` and "
            "`python -m src.preprocess` first."
        )
    return pd.read_parquet(path)


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Return (features, binary label, attack type) from a processed frame."""
    X = df.drop(columns=[config.LABEL_COLUMN, config.ATTACK_TYPE_COLUMN])
    return X, df[config.LABEL_COLUMN], df[config.ATTACK_TYPE_COLUMN]


def make_train_test_split(
    df: pd.DataFrame,
    test_size: float = config.TEST_SIZE,
    random_state: int = config.RANDOM_STATE,
) -> DataSplit:
    """Stratified split on the attack type so rare attack families appear in both sets."""
    X, y, attack = split_features_target(df)
    X_train, X_test, y_train, y_test, attack_train, attack_test = train_test_split(
        X,
        y,
        attack,
        test_size=test_size,
        random_state=random_state,
        stratify=attack,
    )
    return DataSplit(X_train, X_test, y_train, y_test, attack_train, attack_test)


def stratified_subsample(
    X: pd.DataFrame,
    y: pd.Series,
    n_samples: int,
    stratify: pd.Series | None = None,
    random_state: int = config.RANDOM_STATE,
) -> tuple[pd.DataFrame, pd.Series]:
    """Draw a class-proportional subsample, useful for costly models such as SVM."""
    if n_samples >= len(X):
        return X, y
    X_sub, _, y_sub, _ = train_test_split(
        X,
        y,
        train_size=n_samples,
        random_state=random_state,
        stratify=y if stratify is None else stratify,
    )
    return X_sub, y_sub
