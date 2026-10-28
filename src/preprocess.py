"""Cleaning pipeline for the CICIDS2017 MachineLearningCSV files.

Usage:
    python -m src.preprocess

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
DUPLICATED_HEADER_SUFFIX = ".1"


@dataclass
class CleaningReport:
    """Row and column accounting for every cleaning step."""

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


def load_raw(raw_dir: Path = config.RAW_DIR) -> pd.DataFrame:
    """Read and concatenate all raw CSV files.

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


def normalize_labels(labels: pd.Series) -> pd.Series:
    """Strip whitespace and replace non-ASCII dashes with a plain hyphen.

    Example: "Web Attack \\x96 Brute Force" becomes "Web Attack - Brute Force".
    """
    text = labels.astype(str).str.strip()
    text = text.str.replace(r"[^\x00-\x7f]+", "-", regex=True)
    text = text.str.replace(r"\s*-\s*", " - ", regex=True)
    return text.str.replace(r"\s+", " ", regex=True).str.strip()


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean a raw CICIDS2017 frame and add the binary and multiclass targets.

    Steps: drop duplicated header column, normalise labels, remove rows with
    infinite or missing values, remove exact duplicates, remove feature vectors
    that appear with conflicting labels, drop constant columns, cast to float32.
    """
    report = CleaningReport(rows_raw=len(df))
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
    frame[features] = frame[features].apply(pd.to_numeric, errors="coerce")

    values = frame[features]
    infinite = np.isinf(values.to_numpy(dtype="float64", na_value=np.nan)).any(axis=1)
    report.rows_with_infinite = int(infinite.sum())
    frame[features] = values.replace([np.inf, -np.inf], np.nan)
    missing = frame[features].isna().any(axis=1)
    report.rows_with_nan = int(missing.sum())
    frame = frame.loc[~missing]
    report.rows_removed_missing = report.rows_raw - len(frame)

    before = len(frame)
    frame = frame.drop_duplicates()
    report.rows_removed_duplicates = before - len(frame)

    before = len(frame)
    frame = _drop_conflicting(frame, features)
    report.rows_removed_conflicting = before - len(frame)

    constant = [c for c in features if frame[c].nunique(dropna=False) <= 1]
    frame = frame.drop(columns=constant)
    features = [c for c in features if c not in constant]
    report.constant_columns_dropped = constant

    report.negative_value_counts = {
        column: int(count)
        for column, count in (frame[features] < 0).sum().items()
        if count > 0
    }
    frame[features] = frame[features].astype("float32")

    frame[config.ATTACK_TYPE_COLUMN] = frame[RAW_LABEL_COLUMN]
    frame[config.LABEL_COLUMN] = (
        frame[RAW_LABEL_COLUMN] != config.BENIGN_LABEL
    ).astype("int8")
    frame = frame.drop(columns=[RAW_LABEL_COLUMN]).reset_index(drop=True)

    report.rows_final = len(frame)
    report.n_features = len(features)
    report.attack_type_counts_final = _counts(frame[config.ATTACK_TYPE_COLUMN])
    report.binary_counts_final = _counts(frame[config.LABEL_COLUMN])
    return frame, report


def _drop_conflicting(frame: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Remove every row whose feature vector occurs with more than one label."""
    row_hash = pd.util.hash_pandas_object(frame[features], index=False)
    label_count = frame[RAW_LABEL_COLUMN].groupby(row_hash).transform("nunique")
    return frame.loc[label_count == 1]


def _counts(series: pd.Series) -> dict[str, int]:
    return {str(key): int(value) for key, value in series.value_counts().items()}


def run(
    raw_dir: Path = config.RAW_DIR,
    output_file: Path = config.PROCESSED_FILE,
    report_file: Path = config.CLEANING_REPORT_FILE,
) -> CleaningReport:
    """Run the full pipeline and persist the dataset and the cleaning report."""
    cleaned, report = clean(load_raw(raw_dir))
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_parquet(output_file, index=False)
    report_file.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    logger.info("Wrote %s (%d rows, %d features)", output_file, report.rows_final, report.n_features)
    return report


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Clean CICIDS2017 raw CSV files.").parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
