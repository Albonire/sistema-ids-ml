from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.download_data import download_file, is_valid
from src.utils.files import sha256_file


def test_sha256_file_matches_hashlib(tmp_path: Path) -> None:
    path = tmp_path / "x.bin"
    payload = b"intrusion" * 300_000
    path.write_bytes(payload)
    assert sha256_file(path) == hashlib.sha256(payload).hexdigest()


def test_is_valid_detects_missing_and_corrupt(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    assert not is_valid(path, "0" * 64)
    path.write_bytes(b"abc")
    assert is_valid(path, hashlib.sha256(b"abc").hexdigest())
    assert not is_valid(path, "0" * 64)


def test_download_file_verifies_digest(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_bytes(b"a,b\n1,2\n")
    destination = tmp_path / "out.csv"

    with pytest.raises(ValueError, match="SHA256 mismatch"):
        download_file(source.as_uri(), destination, "0" * 64)
    assert not destination.exists()
    assert not destination.with_suffix(".csv.part").exists()

    download_file(source.as_uri(), destination, sha256_file(source))
    assert destination.read_bytes() == source.read_bytes()
