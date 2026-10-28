"""Feature scaler factory. Scalers must be fitted on the training split only."""

from __future__ import annotations

from typing import Literal

from sklearn.preprocessing import MinMaxScaler, StandardScaler

ScalerName = Literal["standard", "minmax"]


def build_scaler(name: ScalerName = "standard") -> StandardScaler | MinMaxScaler:
    """Return an unfitted scaler by name."""
    if name == "standard":
        return StandardScaler()
    if name == "minmax":
        return MinMaxScaler()
    raise ValueError(f"Unknown scaler '{name}'. Use 'standard' or 'minmax'.")
