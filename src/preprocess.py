"""Cleaning pipeline for the CICIDS2017 and UNSW-NB15 datasets.

Usage:
    python -m src.preprocess [--dataset cicids2017|unsw_nb15|all]

Scaling is intentionally not applied here: it must be fitted on the training
split only, otherwise test statistics leak into the model.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from src import config

logger = logging.getLogger(__name__)

RAW_LABEL_COLUMN = "Label"
BINARY_COLUMN = "_is_attack"
DUPLICATED_HEADER_SUFFIX = ".1"


@dataclass
class CleaningReport:
    """Row and column accounting for every cleaning step."""

    dataset: str = ""
    rows_raw: int = 0
    rows_with_infinite: int = 0
    rows_with_nan: int = 0
    rows_removed_missing: int = 0
    rows_removed_duplicates: int = 0
    rows_removed_conflicting: int = 0
    rows_final: int = 0
    duplicated_header_dropped: list[str] = field(default_factory=list)
    constant_columns_dropped: list[str] = field(default_factory=list)
    negative_value_counts: dict[str, int] = field(default_factory=dict)
    attack_type_counts_raw: dict[str, int] = field(default_factory=dict)
    attack_type_counts_final: dict[str, int] = field(default_factory=dict)
    binary_counts_final: dict[str, int] = field(default_factory=dict)
    n_features: int = 0


def load_raw(raw_dir: Path = config.CICIDS2017.raw_dir) -> pd.DataFrame:
    """Read and concatenate all raw CICIDS2017 CSV files.

    The files are not valid UTF-8 (one web attack label contains a cp1252 dash),
    so they are read as latin-1 and labels are normalised later.
    """
    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {raw_dir}. Run `python -m src.download_data` first."
        )
    frames = []
    for path in files:
        frame = pd.read_csv(path, encoding="latin-1", skipinitialspace=True)
        frame.columns = [str(column).strip() for column in frame.columns]
        logger.info("Loaded %s: %d rows", path.name, len(frame))
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load_raw_unsw(raw_dir: Path = config.UNSW_NB15.raw_dir) -> pd.DataFrame:
    """Read and concatenate the UNSW-NB15 training and testing partitions.

    The binary `label` column is validated against `attack_cat` and then dropped,
    the row `id` (a per-file counter) is dropped, and `attack_cat` becomes the
    raw label column with "Normal" renamed to the common BENIGN value.
    """
    files = sorted(raw_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {raw_dir}. Run `python -m src.download_data` first."
        )
    frames = []
    for path in files:
        frame = pd.read_csv(path, encoding="utf-8-sig")
        frame.columns = [str(column).strip() for column in frame.columns]
        logger.info("Loaded %s: %d rows", path.name, len(frame))
        frames.append(frame)
    return normalize_unsw(pd.concat(frames, ignore_index=True))


def normalize_unsw(df: pd.DataFrame) -> pd.DataFrame:
    """Convert a raw UNSW-NB15 frame to the layout expected by `clean`."""
    frame = df.drop(columns=["id"], errors="ignore")
    category = frame["attack_cat"].astype(str).str.strip()
    is_attack = category != "Normal"
    if not (is_attack.astype("int8") == frame["label"]).all():
        raise ValueError("UNSW-NB15 `label` disagrees with `attack_cat`.")
    frame = frame.drop(columns=["label", "attack_cat"])
    frame[RAW_LABEL_COLUMN] = category.where(is_attack, config.BENIGN_LABEL)
    return frame


def normalize_labels(labels: pd.Series) -> pd.Series:
    """Strip whitespace and replace non-ASCII dashes with a plain hyphen.

    Example: "Web Attack \\x96 Brute Force" becomes "Web Attack - Brute Force".
    """
    text = labels.astype(str).str.strip()
    text = text.str.replace(r"[^\x00-\x7f]+", "-", regex=True)
    text = text.str.replace(r"\s*-\s*", " - ", regex=True)
    return text.str.replace(r"\s+", " ", regex=True).str.strip()


def clean(
    df: pd.DataFrame,
    categorical_columns: tuple[str, ...] = (),
    dataset: str = "",
    drop_duplicates: bool = True,
    drop_conflicting: bool = True,
) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean a raw frame and add the binary and multiclass targets.

    Steps: drop duplicated header column, normalise labels, remove rows with
    infinite or missing values, remove duplicate rows, remove feature vectors
    that appear with both a normal and an attack label, drop constant columns, cast numeric
    features to float32. Categorical columns are kept as strings. The two row-removal
    flags exist for the leakage ablation (`src.leakage_ablation`); the pipeline keeps both on.
    """
    report = CleaningReport(dataset=dataset, rows_raw=len(df))
    frame = df.copy()

    duplicated_headers = [c for c in frame.columns if c.endswith(DUPLICATED_HEADER_SUFFIX)]
    for column in duplicated_headers:
        original = column[: -len(DUPLICATED_HEADER_SUFFIX)]
        if not frame[column].equals(frame[original]):
            raise ValueError(f"Column '{column}' differs from '{original}'; refusing to drop it.")
    frame = frame.drop(columns=duplicated_headers)
    report.duplicated_header_dropped = duplicated_headers

    frame[RAW_LABEL_COLUMN] = normalize_labels(frame[RAW_LABEL_COLUMN])
    report.attack_type_counts_raw = _counts(frame[RAW_LABEL_COLUMN])
    features = [c for c in frame.columns if c != RAW_LABEL_COLUMN]
    categorical = [c for c in features if c in categorical_columns]
    numeric = [c for c in features if c not in categorical]
    frame[numeric] = frame[numeric].apply(pd.to_numeric, errors="coerce")
    for column in categorical:
        frame[column] = frame[column].astype(str).str.strip()

    values = frame[numeric]
    infinite = np.isinf(values.to_numpy(dtype="float64", na_value=np.nan)).any(axis=1)
    report.rows_with_infinite = int(infinite.sum())
    frame[numeric] = values.replace([np.inf, -np.inf], np.nan)
    missing = frame[features].isna().any(axis=1)
    report.rows_with_nan = int(missing.sum())
    frame = frame.loc[~missing]
    report.rows_removed_missing = report.rows_raw - len(frame)

    # Cast before deduplicating: rows that differ only below float32 precision are the same
    # vector for the models, and would otherwise leak across the train/test split.
    frame[numeric] = frame[numeric].astype("float32")
    if not np.isfinite(frame[numeric].to_numpy(dtype="float64")).all():
        raise ValueError("Values overflow float32 after casting.")

    # The task is binary, so duplicates and conflicts are judged on the binary label: the same
    # feature vector labelled with two different attack families is a duplicate (the first
    # family is kept), while one labelled both normal and attack is contradictory noise.
    frame[BINARY_COLUMN] = (frame[RAW_LABEL_COLUMN] != config.BENIGN_LABEL).astype("int8")
    before = len(frame)
    if drop_duplicates:
        frame = frame.drop_duplicates(subset=[*features, BINARY_COLUMN])
    report.rows_removed_duplicates = before - len(frame)

    before = len(frame)
    if drop_conflicting:
        frame = _drop_conflicting(frame, features)
    report.rows_removed_conflicting = before - len(frame)

    constant = [c for c in features if frame[c].nunique(dropna=False) <= 1]
    frame = frame.drop(columns=constant)
    features = [c for c in features if c not in constant]
    numeric = [c for c in numeric if c not in constant]
    report.constant_columns_dropped = constant

    report.negative_value_counts = {
        column: int(count)
        for column, count in (frame[numeric] < 0).sum().items()
        if count > 0
    }

    frame[config.ATTACK_TYPE_COLUMN] = frame[RAW_LABEL_COLUMN]
    frame[config.LABEL_COLUMN] = frame[BINARY_COLUMN]
    frame = frame.drop(columns=[RAW_LABEL_COLUMN, BINARY_COLUMN]).reset_index(drop=True)

    report.rows_final = len(frame)
    report.n_features = len(features)
    report.attack_type_counts_final = _counts(frame[config.ATTACK_TYPE_COLUMN])
    report.binary_counts_final = _counts(frame[config.LABEL_COLUMN])
    return frame, report


def _drop_conflicting(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Remove every row whose feature vector occurs with both a normal and an attack label."""
    row_hash = pd.util.hash_pandas_object(frame[features], index=False)
    label_count = frame[BINARY_COLUMN].groupby(row_hash).transform("nunique")
    return frame.loc[label_count == 1]


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts().items()}


def run(dataset: config.DatasetSource = config.CICIDS2017) -> CleaningReport:
    """Run the full pipeline for one dataset and persist the data and the report."""
    raw = load_raw_unsw(dataset.raw_dir) if dataset is config.UNSW_NB15 else load_raw(dataset.raw_dir)
    cleaned, report = clean(raw, dataset.categorical_columns, dataset.key)
    dataset.processed_file.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_parquet(dataset.processed_file, index=False)
    dataset.cleaning_report_file.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    logger.info(
        "Wrote %s (%d rows, %d features)", dataset.processed_file, report.rows_final, report.n_features
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clean the raw dataset files.")
    parser.add_argument("--dataset", choices=[*config.DATASETS, "all"], default="all")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    keys = list(config.DATASETS) if args.dataset == "all" else [args.dataset]
    for key in keys:
        run(config.get_dataset(key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
