"""Evaluation report: figures and a Spanish summary built from the training outputs.

Usage:
    python -m src.evaluate --dataset cicids2017|unsw_nb15

Reads `models/<dataset>/scores.npz` and `reports/<dataset>/{metrics.csv,training_summary.json}`
written by `python -m src.train`, and writes figures plus `resultados.md` under
`reports/<dataset>/`.
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
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402

from src import config  # noqa: E402
from src.metrics import Metrics, bootstrap_intervals  # noqa: E402

logger = logging.getLogger(__name__)

MODEL_ORDER = [
    "rf_baseline",
    "rf_improved",
    "xgb_baseline",
    "xgb_improved",
    "mix_baseline",
    "mix_improved",
]
OPERATING_POINTS = ("default", "recall_target", "fpr_budget")
POINT_LABELS = {
    "default": "umbral 0.5",
    "recall_target": f"mínimo FPR con Recall >= {config.RECALL_TARGET}",
    "fpr_budget": f"máximo Recall con FPR <= {config.FPR_TARGET}",
}
COLORS = {"rf": "#4C78A8", "xgb": "#F58518", "mix": "#54A24B"}
VARIANT_ES = {"baseline": "base", "improved": "mejorado"}
ALGORITHM_ES = {"rf": "Random Forest", "xgb": "XGBoost", "mix": "Mix RF + XGB"}


def pretty(name: str) -> str:
    algorithm, variant = name.split("_")
    return f"{ALGORITHM_ES[algorithm]} ({VARIANT_ES[variant]})"


def _style(name: str) -> dict[str, Any]:
    algorithm, variant = name.split("_")
    return {"color": COLORS[algorithm], "linestyle": "-" if variant == "improved" else "--"}


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_confusion_matrices(scores: Any, summary: dict[str, Any], out: Path) -> None:
    """Row-normalised confusion matrices on test at the recall-target threshold."""
    y = scores["y_test"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 8))
    for ax, name in zip(axes.T.ravel(), MODEL_ORDER):
        predicted = scores[f"{name}_test"] >= summary["thresholds"][name]["recall_target"]
        matrix = np.array(
            [[(predicted[y == t] == p).mean() for p in (False, True)] for t in (0, 1)]
        )
        ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues")
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{matrix[i, j]:.4f}", ha="center", va="center",
                        color="white" if matrix[i, j] > 0.5 else "black")
        ax.set_xticks([0, 1], ["Normal", "Ataque"])
        ax.set_yticks([0, 1], ["Normal", "Ataque"])
        ax.set_xlabel("Predicción")
        ax.set_ylabel("Real")
        ax.set_title(pretty(name), fontsize=10)
    fig.suptitle(f"Matrices de confusión normalizadas (prueba, {POINT_LABELS['recall_target']})")
    _save(fig, out)


def plot_roc(scores: Any, out: Path) -> None:
    """ROC curves on test, linear and log-scaled FPR (the region that matters for an IDS)."""
    y = scores["y_test"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for name in MODEL_ORDER:
        fpr, tpr, _ = roc_curve(y, scores[f"{name}_test"])
        for ax in axes:
            ax.plot(fpr, tpr, label=pretty(name), **_style(name))
    axes[0].plot([0, 1], [0, 1], color="gray", linewidth=0.8)
    axes[0].set_title("Curva ROC")
    axes[1].set_xscale("log")
    axes[1].set_xlim(1e-5, 1)
    axes[1].axvline(config.FPR_TARGET, color="red", linewidth=0.8, linestyle=":")
    axes[1].axhline(config.RECALL_TARGET, color="red", linewidth=0.8, linestyle=":")
    axes[1].set_title("Curva ROC (FPR en escala logarítmica; rojo: criterios del proyecto)")
    for ax in axes:
        ax.set_xlabel("FPR")
        ax.set_ylabel("Recall")
    axes[0].legend(fontsize=8, loc="lower right")
    _save(fig, out)


def plot_precision_recall(scores: Any, out: Path) -> None:
    y = scores["y_test"]
    fig, ax = plt.subplots(figsize=(7, 5))
    for name in MODEL_ORDER:
        precision, recall, _ = precision_recall_curve(y, scores[f"{name}_test"])
        ax.plot(recall, precision, label=pretty(name), **_style(name))
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precisión")
    ax.set_title("Curva Precisión-Recall (prueba)")
    ax.legend(fontsize=8, loc="lower left")
    _save(fig, out)


def plot_fpr_recall(metrics: pd.DataFrame, out: Path) -> None:
    """FPR and Recall on test for every model at the three operating points."""
    test = metrics[metrics["split"] == "test"]
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    positions = np.arange(len(MODEL_ORDER))
    width = 0.27
    for ax, column, title in (
        (axes[0], "fpr", "FPR en prueba (menor es mejor, escala logarítmica)"),
        (axes[1], "recall", "Recall en prueba (mayor es mejor)"),
    ):
        for k, point in enumerate(OPERATING_POINTS):
            values = [
                float(test[(test["model"] == m) & (test["operating_point"] == point)][column].iloc[0])
                for m in MODEL_ORDER
            ]
            ax.bar(positions + (k - 1) * width, values, width=width, label=POINT_LABELS[point])
        ax.set_xticks(positions, [pretty(m).replace(" (", "\n(") for m in MODEL_ORDER], fontsize=7)
        ax.set_title(title, fontsize=10)
    axes[0].set_yscale("log")
    axes[0].axhline(config.FPR_TARGET, color="red", linestyle=":", linewidth=1)
    axes[1].axhline(config.RECALL_TARGET, color="red", linestyle=":", linewidth=1)
    axes[1].set_ylim(0.5, 1.02)
    axes[1].legend(fontsize=7, loc="lower right")
    _save(fig, out)


def detection_by_attack_type(scores: Any, model: str, thresholds: dict[str, float]) -> pd.DataFrame:
    """Share of test flows flagged as attack per family, at each operating point.

    The BENIGN row is the false positive rate; every other row is the detection rate.
    """
    families = pd.Series(scores["attack_test"])
    columns = {
        point: pd.Series(scores[f"{model}_test"] >= thresholds[point]).groupby(families).mean()
        for point in OPERATING_POINTS
    }
    table = pd.DataFrame(columns)
    support = families.value_counts().rename("n")
    return table.join(support).sort_values("recall_target")


def plot_attack_types(table: pd.DataFrame, title: str, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(table) + 2))
    positions = np.arange(len(table))
    height = 0.27
    for k, point in enumerate(OPERATING_POINTS):
        ax.barh(positions + (k - 1) * height, table[point].to_numpy(), height=height, label=POINT_LABELS[point])
    ax.set_yticks(positions, [f"{name} (n={int(n)})" for name, n in zip(table.index, table["n"])], fontsize=8)
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Proporción marcada como ataque (BENIGN = tasa de falsas alarmas)")
    ax.set_title(title, fontsize=10)
    ax.legend(fontsize=7, loc="lower right")
    _save(fig, out)


def plot_importances(summary: dict[str, Any], out: Path, top: int = 15) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))
    for ax, name in zip(axes, ("rf_improved", "xgb_improved")):
        importances = pd.Series(summary["feature_importances"][name]).head(top)[::-1]
        ax.barh(importances.index, importances.values, color=COLORS[name.split("_")[0]])
        ax.set_title(f"Importancia de características: {pretty(name)}")
    _save(fig, out)


def _fmt(value: float) -> str:
    return f"{value:.4f}"


def _as_metrics(row: pd.Series) -> Metrics:
    return Metrics(**{name: row[name] for name in Metrics.__dataclass_fields__})


def _row(test: pd.DataFrame, model: str, point: str) -> pd.Series:
    return test[(test["model"] == model) & (test["operating_point"] == point)].iloc[0]


def write_markdown(
    metrics: pd.DataFrame, summary: dict[str, Any], table: pd.DataFrame, out: Path, dataset_name: str
) -> None:
    """Spanish results summary with the test metrics of every model and operating point."""
    test = metrics[metrics["split"] == "test"]
    best, best_budget = summary["best_model"], summary["best_model_fpr_budget"]
    sizes = summary["split_sizes"]
    lines = [
        f"# Resultados: {dataset_name}",
        "",
        "Generado por `python -m src.evaluate`. Todas las cifras son del conjunto de prueba (15 % de los datos), "
        "que no se usó para ajustar nada: ni hiperparámetros, ni filtro de correlación, ni umbrales, ni la "
        "elección del modelo (todo eso se decidió con entrenamiento y validación).",
        "",
        f"Partición: entrenamiento {sizes['train']:,}, validación {sizes['val']:,}, prueba {sizes['test']:,} "
        f"(estratificada por tipo de ataque, `random_state={summary['random_state']}`).",
        "",
        "Los intervalos de confianza (IC 95 %) son bootstrap exacto sobre la matriz de confusión y reflejan solo "
        "el ruido de muestreo del conjunto de prueba. Dos modelos con intervalos solapados no deben "
        "considerarse distintos.",
        "",
        "## 1. Umbral fijo 0.5 (forma habitual en la literatura)",
        "",
        "| Modelo | Accuracy | Precisión | Recall | F1 | FPR | FPR IC 95 % | ROC-AUC | PR-AUC |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name in MODEL_ORDER:
        r = _row(test, name, "default")
        low, high = bootstrap_intervals(_as_metrics(r))["fpr"]
        lines.append(
            f"| {pretty(name)} | {_fmt(r['accuracy'])} | {_fmt(r['precision'])} | {_fmt(r['recall'])} | "
            f"{_fmt(r['f1'])} | {_fmt(r['fpr'])} | [{_fmt(low)}, {_fmt(high)}] | "
            f"{_fmt(r['roc_auc'])} | {_fmt(r['pr_auc'])} |"
        )
    for point, marker, heading, chosen in (
        ("recall_target", "*", f"## 2. Mínimo FPR con Recall >= {config.RECALL_TARGET} (criterio de AGENT.md)", best),
        ("fpr_budget", "†", f"## 3. Máximo Recall con FPR <= {config.FPR_TARGET} (presupuesto de falsas alarmas)", best_budget),
    ):
        lines += [
            "",
            heading,
            "",
            "El umbral se eligió en validación. Las columnas FP y FN son conteos en prueba.",
            "",
            "| Modelo | Umbral | Recall | Recall IC 95 % | FPR | FPR IC 95 % | Precisión | F1 | FP | FN |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for name in MODEL_ORDER:
            r = _row(test, name, point)
            ci = bootstrap_intervals(_as_metrics(r))
            label = pretty(name) + (f" {marker}" if name == chosen else "")
            lines.append(
                f"| {label} | {r['threshold']:.4f} | {_fmt(r['recall'])} | "
                f"[{_fmt(ci['recall'][0])}, {_fmt(ci['recall'][1])}] | {_fmt(r['fpr'])} | "
                f"[{_fmt(ci['fpr'][0])}, {_fmt(ci['fpr'][1])}] | {_fmt(r['precision'])} | {_fmt(r['f1'])} | "
                f"{int(r['fp'])} | {int(r['fn'])} |"
            )
    lines += [
        "",
        "`*` = modelo elegido en validación con el criterio de AGENT.md. `†` = modelo con mayor Recall en "
        "validación bajo el presupuesto de FPR.",
        "",
        "## Modelo seleccionado",
        "",
        f"Modelo (criterio AGENT.md): {pretty(best)}.",
        "",
        "| Punto de operación | Recall | FPR | Cumple Recall >= "
        f"{config.RECALL_TARGET} y FPR <= {config.FPR_TARGET} |",
        "|---|---|---|---|",
    ]
    for point in OPERATING_POINTS:
        r = _row(test, best, point)
        meets = r["recall"] >= config.RECALL_TARGET and r["fpr"] <= config.FPR_TARGET
        lines.append(f"| {POINT_LABELS[point]} | {_fmt(r['recall'])} | {_fmt(r['fpr'])} | {'sí' if meets else 'no'} |")
    lines += [
        "",
        f"## Detección por tipo de ataque ({pretty(best)}, prueba)",
        "",
        "Proporción de flujos marcados como ataque. En BENIGN es la tasa de falsas alarmas. "
        "Las familias con pocos flujos de prueba (columna n) tienen estimaciones muy inestables.",
        "",
        "| Tipo | n | umbral 0.5 | Recall >= objetivo | FPR <= presupuesto |",
        "|---|---|---|---|---|",
    ]
    for name, row in table.sort_values("recall_target", ascending=False).iterrows():
        suffix = " (falsas alarmas)" if name == config.BENIGN_LABEL else ""
        lines.append(
            f"| {name}{suffix} | {int(row['n'])} | {_fmt(row['default'])} | "
            f"{_fmt(row['recall_target'])} | {_fmt(row['fpr_budget'])} |"
        )
    lines += [
        "",
        "## Figuras",
        "",
        "- `figures/confusion_matrices.png`",
        "- `figures/roc.png`",
        "- `figures/precision_recall.png`",
        "- `figures/fpr_recall_comparison.png`",
        "- `figures/detection_by_attack_type.png`",
        "- `figures/feature_importances.png`",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def run(dataset_key: str) -> None:
    dataset = config.get_dataset(dataset_key)
    scores = np.load(dataset.models_dir / "scores.npz")
    metrics = pd.read_csv(dataset.reports_dir / "metrics.csv")
    summary = json.loads((dataset.reports_dir / "training_summary.json").read_text(encoding="utf-8"))
    figures = dataset.reports_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    best = summary["best_model"]
    table = detection_by_attack_type(scores, best, summary["thresholds"][best])

    plot_confusion_matrices(scores, summary, figures / "confusion_matrices.png")
    plot_roc(scores, figures / "roc.png")
    plot_precision_recall(scores, figures / "precision_recall.png")
    plot_fpr_recall(metrics, figures / "fpr_recall_comparison.png")
    plot_attack_types(table, f"{dataset.display_name}: {pretty(best)}", figures / "detection_by_attack_type.png")
    plot_importances(summary, figures / "feature_importances.png")
    write_markdown(metrics, summary, table, dataset.reports_dir / "resultados.md", dataset.display_name)
    logger.info("Wrote report to %s", dataset.reports_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the evaluation report.")
    parser.add_argument("--dataset", choices=list(config.DATASETS), required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(args.dataset)
    return 0


if __name__ == "__main__":
    sys.exit(main())
