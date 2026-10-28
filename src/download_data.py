"""Download the CICIDS2017 MachineLearningCSV files with integrity verification.

Usage:
    python -m src.download_data [--force]
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

MANUAL_HINT = (
    "If the automatic download keeps failing, download MachineLearningCSV.zip "
    "manually from https://www.unb.ca/cic/datasets/ids-2017.html and extract the "
    f"CSV files into {config.RAW_DIR}."
)


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


def download_all(raw_dir: Path = config.RAW_DIR, force: bool = False) -> list[Path]:
    """Download every dataset file that is missing or corrupted."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, expected in config.RAW_FILES_SHA256.items():
        destination = raw_dir / name
        if not force and is_valid(destination, expected):
            logger.info("OK (cached): %s", name)
        else:
            logger.info("Downloading: %s", name)
            download_file(f"{config.MIRROR_BASE_URL}/{name}", destination, expected)
            logger.info("OK (verified): %s", name)
        paths.append(destination)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download CICIDS2017 CSV files.")
    parser.add_argument("--force", action="store_true", help="re-download all files")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        download_all(force=args.force)
    except (urllib.error.URLError, OSError, ValueError) as error:
        logger.error("Download failed: %s", error)
        logger.error(MANUAL_HINT)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
