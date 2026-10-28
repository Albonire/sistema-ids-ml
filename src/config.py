"""Central configuration: repository-relative paths, constants and dataset sources."""

from __future__ import annotations

from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
RAW_DIR: Final[Path] = DATA_DIR / "raw"
PROCESSED_DIR: Final[Path] = DATA_DIR / "processed"
MODELS_DIR: Final[Path] = PROJECT_ROOT / "models"

PROCESSED_FILE: Final[Path] = PROCESSED_DIR / "cicids2017_clean.parquet"
CLEANING_REPORT_FILE: Final[Path] = PROCESSED_DIR / "cleaning_report.json"

RANDOM_STATE: Final[int] = 42
TEST_SIZE: Final[float] = 0.30

# Column names produced by the preprocessing step.
LABEL_COLUMN: Final[str] = "label"
ATTACK_TYPE_COLUMN: Final[str] = "attack_type"
BENIGN_LABEL: Final[str] = "BENIGN"

# The official UNB download now requires a registration form, so the original
# MachineLearningCSV files are fetched from a Hugging Face mirror pinned to a
# fixed revision. Integrity is guaranteed by the SHA256 digests below.
MIRROR_REPO: Final[str] = "c01dsnap/CIC-IDS2017"
MIRROR_REVISION: Final[str] = "4e9edfa727f800b6f595bc2ee7420527156562b2"
MIRROR_BASE_URL: Final[str] = (
    f"https://huggingface.co/datasets/{MIRROR_REPO}/resolve/{MIRROR_REVISION}"
)

RAW_FILES_SHA256: Final[dict[str, str]] = {
    "Monday-WorkingHours.pcap_ISCX.csv": "852c4beb34eda186f32561fa79df7a0747e92e1a6535b01270820dd9ffe17f34",
    "Tuesday-WorkingHours.pcap_ISCX.csv": "52b8692ae8c7d2ed04671fe2b98335693c0a92c7ab157d8c8b534d6523080851",
    "Wednesday-workingHours.pcap_ISCX.csv": "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": "d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": "6bcda3857c2504676034e3ea57762d38393cc734cb377a726bd5cb153961b1b5",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv": "53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": "ca1824c51bfbb7b3c72290a11be04366ba8815878c6a1cc5c44cb1cee269e99b",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": "6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee",
}
