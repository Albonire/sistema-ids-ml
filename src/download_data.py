"""Download the project datasets with integrity verification.

Usage:
    python -m src.download_data [--dataset cicids2017|unsw_nb15|all] [--force]
"""

from __future__ import annotations

import argparse
import logging
import sys
import urllib.error
import urllib.request
from pathlib import Path

from src import config
from src.utils.files import sha256_file

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1024 * 1024
_TIMEOUT_SECONDS = 60

MANUAL_HINTS = {
    "cicids2017": (
        "Download MachineLearningCSV.zip manually from "
        "https://www.unb.ca/cic/datasets/ids-2017.html and extract the CSV files into {raw_dir}."
    ),
    "unsw_nb15": (
        "Download the training and testing set CSV files manually from "
        "https://research.unsw.edu.au/projects/unsw-nb15-dataset into {raw_dir}."
    ),
}


def is_valid(path: Path, expected_sha256: str) -> bool:
    """Return True when the file exists and matches the expected digest."""
    return path.is_file() and sha256_file(path) == expected_sha256


def download_file(url: str, destination: Path, expected_sha256: str) -> None:
    """Stream a URL to disk, verify its SHA256 and move it atomically into place."""
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "sistema-ids-ml/1.0"})
    with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        with partial.open("wb") as handle:
            while chunk := response.read(_CHUNK_SIZE):
                handle.write(chunk)
    actual = sha256_file(partial)
    if actual != expected_sha256:
        partial.unlink(missing_ok=True)
        raise ValueError(
            f"SHA256 mismatch for {destination.name}: expected {expected_sha256}, got {actual}"
        )
    partial.replace(destination)


def download_all(
    dataset: config.DatasetSource = config.CICIDS2017,
    raw_dir: Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Download every file of a dataset that is missing or corrupted."""
    raw_dir = raw_dir or dataset.raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, expected in dataset.files_sha256.items():
        destination = raw_dir / name
        if not force and is_valid(destination, expected):
            logger.info("OK (cached): %s", name)
        else:
            logger.info("Downloading: %s", name)
            download_file(f"{dataset.base_url}/{name}", destination, expected)
            logger.info("OK (verified): %s", name)
        paths.append(destination)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download the project datasets.")
    parser.add_argument("--dataset", choices=[*config.DATASETS, "all"], default="all")
    parser.add_argument("--force", action="store_true", help="re-download all files")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    keys = list(config.DATASETS) if args.dataset == "all" else [args.dataset]
    for key in keys:
        dataset = config.get_dataset(key)
        logger.info("Dataset: %s", dataset.display_name)
        try:
            download_all(dataset, force=args.force)
        except (urllib.error.URLError, OSError, ValueError) as error:
            logger.error("Download failed: %s", error)
            logger.error(MANUAL_HINTS[key].format(raw_dir=dataset.raw_dir))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
