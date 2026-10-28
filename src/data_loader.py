"""Deterministic loading and splitting of the processed datasets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

from src import config


@dataclass(frozen=True)
class Partition:
    """Features, binary target and multiclass attack type of one data partition."""

    X: pd.DataFrame
    y: pd.Series
    attack: pd.Series

    def __len__(self) -> int:
        return len(self.X)


@dataclass(frozen=True)
class DataSplits:
    """Train, validation and test partitions."""

    train: Partition
    val: Partition
    test: Partition

    @property
    def feature_names(self) -> list[str]:
        return list(self.train.X.columns)


def load_processed(dataset: str = "cicids2017", path: Path | None = None) -> pd.DataFrame:
    """Load the cleaned dataset produced by `python -m src.preprocess`."""
    path = path or config.get_dataset(dataset).processed_file
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


def make_splits(
    df: pd.DataFrame,
    val_size: float = config.VAL_SIZE,
    test_size: float = config.TEST_SIZE,
    random_state: int = config.RANDOM_STATE,
) -> DataSplits:
    """Stratified train/validation/test split (70/15/15 by default).

    Stratification uses the attack type so rare attack families appear in every
    partition. The test set is carved out first and must stay untouched until the
    final evaluation; the validation set is used for tuning and threshold choice.
    """
    X, y, attack = split_features_target(df)
    X_rest, X_test, y_rest, y_test, attack_rest, attack_test = train_test_split(
        X, y, attack, test_size=test_size, random_state=random_state, stratify=attack
    )
    relative_val = val_size / (1.0 - test_size)
    X_train, X_val, y_train, y_val, attack_train, attack_val = train_test_split(
        X_rest,
        y_rest,
        attack_rest,
        test_size=relative_val,
        random_state=random_state,
        stratify=attack_rest,
    )
    return DataSplits(
        train=Partition(X_train, y_train, attack_train),
        val=Partition(X_val, y_val, attack_val),
        test=Partition(X_test, y_test, attack_test),
    )


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
