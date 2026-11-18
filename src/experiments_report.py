"""Spanish report and figures for the formal experiments.

Usage:
    python -m src.experiments_report --dataset unsw_nb15|cicids2017

Reads the CSV files written by `python -m src.experiments` and writes
`reports/<dataset>/experimentos.md` plus figures under `reports/<dataset>/figures/`.
Sections whose input file does not exist are skipped.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import config  # noqa: E402
from src.evaluate import COLORS, MODEL_ORDER, POINT_LABELS, pretty  # noqa: E402
from src.train import OPERATING_POINTS  # noqa: E402

logger = logging.getLogger(__name__)

PAIR_TEXT = {
    ("rf_improved", "rf_baseline"): "RF mejorado frente a RF base",
    ("xgb_improved", "xgb_baseline"): "XGBoost mejorado frente a XGBoost base",
    ("mix_improved", "mix_baseline"): "Mix mejorado frente a Mix base",
    ("xgb_improved", "rf_improved"): "XGBoost mejorado frente a RF mejorado",
    ("xgb_baseline", "rf_baseline"): "XGBoost base frente a RF base",
    ("mix_improved", "xgb_improved"): "Mix mejorado frente a XGBoost mejorado",
    ("mix_baseline", "xgb_baseline"): "Mix base frente a XGBoost base",
}
PROTOCOL_TEXT = {
    "A_oficial_ingenuo": "A. Particiones oficiales, sin depurar (como la literatura)",
    "B_oficial_depurado": "B. Particiones oficiales, depuradas y sin vectores repetidos entre ellas",
    "C_cv5_ingenuo": "C1. Validación cruzada de 5 folds sobre el entrenamiento oficial, sin depurar",
    "C_cv5_depurado": "C2. Validación cruzada de 5 folds sobre el entrenamiento oficial, depurado",
}
SHORT_POINT = {
    "default": "umbral 0.5",
    "recall_target": f"Recall >= {config.RECALL_TARGET}",
    "fpr_budget": f"FPR <= {config.FPR_TARGET}",
}


def _pmr(row: Any, metric: str, digits: int = 4) -> str:
    """'mean ± std' of one summary metric taken from a row of `multiseed_summary.csv`."""
    return _pm(float(row[f"{metric}_mean"]), float(row[f"{metric}_std"]), digits)


def _pm(mean: float, std: float, digits: int = 4) -> str:
    """Format 'mean ± standard deviation'; a missing deviation (one seed) prints as zero."""
    return f"{mean:.{digits}f} ± {0.0 if np.isnan(std) else std:.{digits}f}"


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_multiseed(summary: pd.DataFrame, out: Path) -> None:
    """Mean and standard deviation over seeds of Recall and FPR, per model and operating point."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for col, point in enumerate(OPERATING_POINTS):
        rows = summary[summary["operating_point"] == point].set_index("model").loc[MODEL_ORDER]
        positions = np.arange(len(MODEL_ORDER))
        colors = [COLORS[m.split("_")[0]] for m in MODEL_ORDER]
        for row, metric in enumerate(("recall", "fpr")):
            ax = axes[row, col]
            ax.bar(
                positions,
                rows[f"{metric}_mean"],
                yerr=rows[f"{metric}_std"].fillna(0),
                color=colors,
                capsize=4,
                alpha=0.9,
            )
            ax.set_xticks(positions, [pretty(m).replace(" (", "\n(") for m in MODEL_ORDER], fontsize=7)
            ax.set_title(f"{metric.upper() if metric == 'fpr' else 'Recall'}: {SHORT_POINT[point]}", fontsize=10)
            low = float((rows[f"{metric}_mean"] - 3 * rows[f"{metric}_std"].fillna(0)).min())
            high = float((rows[f"{metric}_mean"] + 3 * rows[f"{metric}_std"].fillna(0)).max())
            pad = max((high - low) * 0.15, 1e-4)
            ax.set_ylim(max(0.0, low - pad), high + pad)
    fig.suptitle("Media y desviación estándar sobre las semillas (prueba)")
    _save(fig, out)


def plot_pairwise(pairs: pd.DataFrame, out: Path) -> None:
    """Forest plot of the paired differences that matter at the two calibrated points."""
    selection = [
        ("recall_target", "fpr", "Diferencia de FPR con Recall >= 0.95 (menor es mejor)"),
        ("fpr_budget", "recall", "Diferencia de Recall con FPR <= 0.02 (mayor es mejor)"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
    labels = [PAIR_TEXT[p] for p in PAIR_TEXT]
    for ax, (point, metric, title) in zip(axes, selection, strict=False):
        for i, pair in enumerate(PAIR_TEXT):
            row = pairs[
                (pairs["model_a"] == pair[0])
                & (pairs["model_b"] == pair[1])
                & (pairs["operating_point"] == point)
                & (pairs["metric"] == metric)
            ].iloc[0]
            significant = row["p_value"] < 0.05
            ax.errorbar(
                row["difference"],
                i,
                xerr=[[row["difference"] - row["low"]], [row["high"] - row["difference"]]],
                fmt="o",
                color="#d03b3b" if significant else "#898781",
                capsize=4,
            )
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_yticks(range(len(labels)), labels, fontsize=8)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=10)
    fig.suptitle("Pruebas pareadas (bootstrap, IC 95 %). Rojo: p < 0.05")
    _save(fig, out)


def plot_ablation(table: pd.DataFrame, out: Path) -> None:
    """FPR at the Recall target and Recall at the FPR budget for every feature group."""
    groups = list(dict.fromkeys(table["group"]))
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
    for ax, (point, metric, title) in zip(
        axes,
        [
            ("recall_target", "fpr", "FPR con Recall >= 0.95 (menor es mejor)"),
            ("fpr_budget", "recall", "Recall con FPR <= 0.02 (mayor es mejor)"),
        ], strict=False,
    ):
        values = [
            float(table[(table["group"] == g) & (table["operating_point"] == point)][metric].iloc[0])
            for g in groups
        ]
        ax.barh(range(len(groups)), values, color=["#2a78d6"] + ["#eb6834"] * (len(groups) - 1))
        ax.set_yticks(range(len(groups)), groups, fontsize=8)
        ax.invert_yaxis()
        for i, value in enumerate(values):
            ax.text(value, i, f" {value:.4f}", va="center", fontsize=8)
        ax.set_xlim(min(values) * 0.9, max(values) * 1.08)
        ax.set_title(title, fontsize=10)
    fig.suptitle("Ablación de variables (XGBoost mejorado, prueba)")
    _save(fig, out)


def seeds_section(dataset: config.DatasetSource) -> list[str]:
    """Markdown lines of the multi-seed section."""
    summary_path = dataset.reports_dir / "multiseed_summary.csv"
    if not summary_path.is_file():
        return []
    summary = pd.read_csv(summary_path)
    info = json.loads((dataset.reports_dir / "multiseed_summary.json").read_text(encoding="utf-8"))
    seeds = info["seeds"]
    lines = [
        "## 1. Repetición con varias semillas",
        "",
        f"Se repitió la partición 70/15/15 y el ajuste de los seis modelos con las semillas {seeds}. "
        "Cada celda es media ± desviación estándar muestral sobre las semillas, en el conjunto de prueba. "
        f"Los hiperparámetros de las versiones mejoradas son los de la búsqueda con la semilla "
        f"{info['hyperparameters_from_seed']} y no se volvieron a buscar; además, esos datos de "
        "ajuste se solapan con las pruebas de las otras semillas. Por eso la desviación subestima "
        "la variación real de repetir también la búsqueda.",
        "",
    ]
    for point in OPERATING_POINTS:
        lines += [
            f"### {POINT_LABELS[point].capitalize()}",
            "",
            "| Modelo | Recall | FPR | Precisión | Accuracy | ROC-AUC |",
            "|---|---|---|---|---|---|",
        ]
        rows = summary[summary["operating_point"] == point].set_index("model")
        for name in MODEL_ORDER:
            r = rows.loc[name]
            lines.append(
                f"| {pretty(name)} | {_pmr(r, 'recall')} | {_pmr(r, 'fpr', 5)} | "
                f"{_pmr(r, 'precision')} | {_pmr(r, 'accuracy')} | {_pmr(r, 'roc_auc')} |"
            )
        lines.append("")
    wins = pd.DataFrame(info["best_by_seed"]).T
    lines += [
        "### Qué modelo gana en cada semilla",
        "",
        "| Semilla | Regla de AGENT.md (mínimo FPR con Recall >= 0.95) | Presupuesto (máximo Recall con FPR <= 0.02) |",
        "|---|---|---|",
    ]
    for seed, row in wins.iterrows():
        lines.append(f"| {seed} | {pretty(row['recall_target'])} | {pretty(row['fpr_budget'])} |")
    counts_rt = wins["recall_target"].map(pretty).value_counts()
    counts_fb = wins["fpr_budget"].map(pretty).value_counts()
    lines += [
        "",
        "Victorias con la regla de AGENT.md: "
        + ", ".join(f"{name} {n}" for name, n in counts_rt.items())
        + ". Victorias con el presupuesto de FPR: "
        + ", ".join(f"{name} {n}" for name, n in counts_fb.items())
        + ".",
        "",
    ]
    reproduction = info.get("primary_reproduction")
    if reproduction:
        lines += [
            f"Reproducibilidad: al reentrenar la semilla {config.RANDOM_STATE} se obtienen las mismas "
            f"métricas guardadas (diferencia absoluta máxima {reproduction['max_abs_difference']:.2e}).",
            "",
        ]
    lines += ["![Media y desviación sobre semillas](figures/multiseed.png)", ""]
    return lines


def pairwise_section(dataset: config.DatasetSource) -> list[str]:
    """Markdown lines of the paired-tests section."""
    path = dataset.reports_dir / "pairwise_tests.csv"
    if not path.is_file():
        return []
    table = pd.read_csv(path)
    lines = [
        "## 2. Pruebas pareadas entre modelos",
        "",
        "Bootstrap pareado sobre las mismas filas de prueba (semilla 42), cada modelo con su propio umbral "
        "elegido en validación. Diferencia = A menos B, con IC 95 % y p bilateral. Mide solo el ruido de "
        "muestreo de la prueba. A diferencia de comparar intervalos separados (que pueden solaparse aunque "
        "haya diferencia), la prueba pareada aprovecha que ambos modelos ven los mismos flujos.",
        "",
        "| Comparación | Punto de operación | Diferencia de Recall [IC 95 %] (p) | Diferencia de FPR [IC 95 %] (p) |",
        "|---|---|---|---|",
    ]

    def cell(row: Any, digits: int) -> str:
        """Format a paired difference with its interval and p-value."""
        d, lo, hi, p = (float(row[k]) for k in ("difference", "low", "high", "p_value"))
        return f"{d:+.{digits}f} [{lo:+.{digits}f}, {hi:+.{digits}f}] (p={p:.3f})"

    for pair, text in PAIR_TEXT.items():
        for point in OPERATING_POINTS:
            subset = table[
                (table["model_a"] == pair[0]) & (table["model_b"] == pair[1]) & (table["operating_point"] == point)
            ].set_index("metric")
            lines.append(
                f"| {text} | {SHORT_POINT[point]} | {cell(subset.loc['recall'], 4)} | "
                f"{cell(subset.loc['fpr'], 4)} |"
            )
    lines += ["", "![Diferencias pareadas](figures/pairwise.png)", ""]
    return lines


def official_section(dataset: config.DatasetSource) -> list[str]:
    """Markdown lines of the official-partitions section."""
    path = dataset.reports_dir / "official_partitions.csv"
    if not path.is_file():
        return []
    table = pd.read_csv(path)
    lines = [
        "## 3. Particiones oficiales de UNSW-NB15",
        "",
        "Modelos base (RF y XGBoost del Entregable 1) con umbral 0.5. La partición oficial de "
        "entrenamiento tiene 175.341 flujos y la de prueba 82.332. 'Prueba repetida' es la fracción de "
        "filas de prueba cuyo vector exacto aparece en el entrenamiento.",
        "",
        "| Protocolo | Modelo | Entrenamiento | Prueba | Prueba repetida | Accuracy | Recall | FPR | ROC-AUC |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for protocol, text in PROTOCOL_TEXT.items():
        part = table[table["protocol"] == protocol]
        for model in ("rf_baseline", "xgb_baseline"):
            rows = part[part["model"] == model]
            if rows.empty:
                continue
            if protocol.startswith("C_"):
                cell = {m: _pm(rows[m].mean(), rows[m].std()) for m in ("accuracy", "recall", "fpr", "roc_auc")}
                size_train, size_test = int(rows["n_train"].mean()), int(rows["n_test"].mean())
            else:
                cell = {m: f"{rows[m].iloc[0]:.4f}" for m in ("accuracy", "recall", "fpr", "roc_auc")}
                size_train, size_test = int(rows["n_train"].iloc[0]), int(rows["n_test"].iloc[0])
            lines.append(
                f"| {text} | {pretty(model)} | {size_train:,} | {size_test:,} | "
                f"{100 * rows['leaked_test_share'].mean():.1f} % | {cell['accuracy']} | {cell['recall']} | "
                f"{cell['fpr']} | {cell['roc_auc']} |".replace(",", ".")
            )
    lines += [
        "",
        "En las filas C se promedian los 5 folds (media ± desviación estándar).",
        "",
    ]
    return lines


def ablation_section(dataset: config.DatasetSource) -> list[str]:
    """Markdown lines of the feature-ablation section."""
    path = dataset.reports_dir / "feature_ablation.csv"
    if not path.is_file():
        return []
    table = pd.read_csv(path)
    lines = [
        f"## 4. Ablación de variables ({dataset.display_name})",
        "",
        "XGBoost con los hiperparámetros de la versión mejorada, reentrenado sin cada grupo de variables "
        "sospechosas de actuar como atajo. Los umbrales se vuelven a elegir en validación. Que el "
        "rendimiento no baje al quitar un grupo no prueba que el modelo no use atajos, porque otras "
        "variables correlacionadas pueden tomar su lugar; sí muestra que el rendimiento no depende de ese grupo.",
        "",
        "| Grupo quitado | Variables | Recall (umbral 0.5) | FPR (umbral 0.5) | FPR con Recall >= 0.95 "
        "| Recall con FPR <= 0.02 | ROC-AUC |",
        "|---|---|---|---|---|---|---|",
    ]
    for group in dict.fromkeys(table["group"]):
        rows = table[table["group"] == group].set_index("operating_point")
        dropped = rows["dropped"].iloc[0]
        dropped = dropped if isinstance(dropped, str) and dropped else "ninguna"
        lines.append(
            f"| {group} | {dropped} | {rows.loc['default', 'recall']:.4f} | {rows.loc['default', 'fpr']:.4f} | "
            f"{rows.loc['recall_target', 'fpr']:.4f} | {rows.loc['fpr_budget', 'recall']:.4f} | "
            f"{rows.loc['default', 'roc_auc']:.4f} |"
        )
    lines += ["", "![Ablación de variables](figures/feature_ablation.png)", ""]
    return lines


def run(dataset_key: str) -> Path:
    """Write the Spanish report and the figures of a dataset."""
    dataset = config.get_dataset(dataset_key)
    figures = dataset.reports_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Experimentos formales: {dataset.display_name}",
        "",
        "Generado por `python -m src.experiments_report`. Todas las cifras son del conjunto de prueba "
        "salvo que se indique otra cosa.",
        "",
    ]
    if (dataset.reports_dir / "multiseed_summary.csv").is_file():
        plot_multiseed(pd.read_csv(dataset.reports_dir / "multiseed_summary.csv"), figures / "multiseed.png")
    if (dataset.reports_dir / "pairwise_tests.csv").is_file():
        plot_pairwise(pd.read_csv(dataset.reports_dir / "pairwise_tests.csv"), figures / "pairwise.png")
    if (dataset.reports_dir / "feature_ablation.csv").is_file():
        plot_ablation(pd.read_csv(dataset.reports_dir / "feature_ablation.csv"), figures / "feature_ablation.png")
    for section in (seeds_section, pairwise_section, official_section, ablation_section):
        lines += section(dataset)
    out = dataset.reports_dir / "experimentos.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="Report for the formal experiments.")
    parser.add_argument("--dataset", choices=list(config.DATASETS), required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Wrote %s", run(args.dataset))
    return 0


if __name__ == "__main__":
    sys.exit(main())
