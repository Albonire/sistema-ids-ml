"""Central configuration: repository-relative paths, constants and dataset sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DATA_DIR: Final[Path] = PROJECT_ROOT / "data"
RAW_DIR: Final[Path] = DATA_DIR / "raw"
PROCESSED_DIR: Final[Path] = DATA_DIR / "processed"
MODELS_DIR: Final[Path] = PROJECT_ROOT / "models"
REPORTS_DIR: Final[Path] = PROJECT_ROOT / "reports"

RANDOM_STATE: Final[int] = 42
VAL_SIZE: Final[float] = 0.15
TEST_SIZE: Final[float] = 0.15

# Decision criterion from AGENT.md section 6.
RECALL_TARGET: Final[float] = 0.95
FPR_TARGET: Final[float] = 0.02

# Column names produced by the preprocessing step.
LABEL_COLUMN: Final[str] = "label"
ATTACK_TYPE_COLUMN: Final[str] = "attack_type"
BENIGN_LABEL: Final[str] = "BENIGN"


@dataclass(frozen=True)
class DatasetSource:
    """Where a dataset comes from and where its derived files live."""

    key: str
    display_name: str
    base_url: str
    files_sha256: dict[str, str]
    categorical_columns: tuple[str, ...] = ()

    @property
    def raw_dir(self) -> Path:
        return RAW_DIR / self.key

    @property
    def processed_file(self) -> Path:
        return PROCESSED_DIR / f"{self.key}_clean.parquet"

    @property
    def cleaning_report_file(self) -> Path:
        return PROCESSED_DIR / f"{self.key}_cleaning_report.json"

    @property
    def models_dir(self) -> Path:
        return MODELS_DIR / self.key

    @property
    def reports_dir(self) -> Path:
        return REPORTS_DIR / self.key


# The official UNB download for CICIDS2017 now requires a registration form, so the
# original MachineLearningCSV files are fetched from a Hugging Face mirror pinned to
# a fixed revision. Integrity is guaranteed by the SHA256 digests below.
CICIDS2017_REVISION: Final[str] = "4e9edfa727f800b6f595bc2ee7420527156562b2"
CICIDS2017 = DatasetSource(
    key="cicids2017",
    display_name="CICIDS2017",
    base_url=f"https://huggingface.co/datasets/c01dsnap/CIC-IDS2017/resolve/{CICIDS2017_REVISION}",
    files_sha256={
        "Monday-WorkingHours.pcap_ISCX.csv": "852c4beb34eda186f32561fa79df7a0747e92e1a6535b01270820dd9ffe17f34",
        "Tuesday-WorkingHours.pcap_ISCX.csv": "52b8692ae8c7d2ed04671fe2b98335693c0a92c7ab157d8c8b534d6523080851",
        "Wednesday-workingHours.pcap_ISCX.csv": "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a",
        "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": "d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d",
        "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": "6bcda3857c2504676034e3ea57762d38393cc734cb377a726bd5cb153961b1b5",
        "Friday-WorkingHours-Morning.pcap_ISCX.csv": "53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000",
        "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": "ca1824c51bfbb7b3c72290a11be04366ba8815878c6a1cc5c44cb1cee269e99b",
        "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": "6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee",
    },
)

# UNSW-NB15 official training and testing partitions (175,341 and 82,332 rows). The
# mirror has the two file names swapped: "test.csv" holds the training partition.
# Both are concatenated and re-split by this project, so the swap has no effect.
UNSW_NB15_REVISION: Final[str] = "3eb02c4a0a29866b7abcb5ef77c45cf4fcc8f6b0"
UNSW_NB15 = DatasetSource(
    key="unsw_nb15",
    display_name="UNSW-NB15",
    base_url=f"https://huggingface.co/datasets/Mireu-Lab/UNSW-NB15/resolve/{UNSW_NB15_REVISION}",
    files_sha256={
        "train.csv": "734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559",
        "test.csv": "bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa",
    },
    categorical_columns=("proto", "service", "state"),
)

DATASETS: Final[dict[str, DatasetSource]] = {
    CICIDS2017.key: CICIDS2017,
    UNSW_NB15.key: UNSW_NB15,
}


def get_dataset(key: str) -> DatasetSource:
    """Return a dataset source by key, with a helpful error for unknown keys."""
    try:
        return DATASETS[key]
    except KeyError as error:
        raise ValueError(f"Unknown dataset '{key}'. Choose from: {', '.join(DATASETS)}.") from error
