"""Figures for the final report, the study guide and the slides (real data, no mock-ups).

Usage (from the repository root):
    python docs/entrega/make_figures.py

Every chart reads the files produced by the pipeline (`reports/`, `models/`, `data/processed/`),
so a number on a figure is always the number in the reports. Output: PNG at 200 dpi in
`docs/entrega/figuras/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from sklearn.metrics import roc_curve  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402

OUT = Path(__file__).resolve().parent / "figuras"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
CRITICAL, GOOD, MUTED, INK = "#d03b3b", "#0ca30c", "#898781", "#1f2430"
POINTS = ("default", "recall_target", "fpr_budget")
POINT_NAME = {
    "default": "Umbral 0.5",
    "recall_target": "Mínimo FPR con Recall >= 0.95",
    "fpr_budget": "Máximo Recall con FPR <= 0.02",
}
POINT_COLOR = {"default": MUTED, "recall_target": ORANGE, "fpr_budget": BLUE}

plt.rcParams.update(
    {
        "font.family": "Inter",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "figure.facecolor": "white",
    }
)


def _save(fig: plt.Figure, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(n: float) -> str:
    return f"{int(n):,}".replace(",", " ")


# ------------------------------------------------------------------ architecture


def _box(ax, x, y, w, h, text, color, text_color="white", size=10.5) -> None:
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=color, ec="none"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", color=text_color, fontsize=size, fontweight="bold", wrap=True)


def _arrow(ax, x1, y1, x2, y2) -> None:
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16, color=INK, lw=1.6))


def architecture() -> None:
    """Pipeline from raw files to the demo, with the module that implements each stage."""
    fig, ax = plt.subplots(figsize=(13.4, 5.4))
    ax.set_xlim(0, 13.0)
    ax.set_ylim(0, 5.4)
    ax.axis("off")
    stages = [
        ("1. Datos crudos", "CICIDS2017\nUNSW-NB15", MUTED, "download_data.py"),
        ("2. Limpieza", "inf/NaN, duplicados,\ncontradictorios", BLUE, "preprocess.py"),
        ("3. Partición", "70 / 15 / 15\nestratificada", AQUA, "data_loader.py"),
        ("4. Entrenamiento", "RF, XGBoost y Mix\nbase y mejorado", ORANGE, "train.py, models.py"),
        ("5. Umbrales", "3 puntos de operación\nelegidos en validación", YELLOW, "metrics.py"),
        ("6. Evaluación", "prueba, IC bootstrap,\nexperimentos", CRITICAL, "evaluate.py"),
    ]
    width, gap, top, height = 1.8, 0.35, 3.0, 2.0
    centers = []
    for i, (title, body, color, module) in enumerate(stages):
        x = 0.2 + i * (width + gap)
        ink = INK if color == YELLOW else "white"
        _box(ax, x, top, width, height, f"{title}\n\n{body}", color, ink, 9.2)
        ax.text(x + width / 2, top + 0.2, module, ha="center", va="center", fontsize=7.6, color=ink, family="JetBrains Mono")
        centers.append(x + width / 2)
        if i < len(stages) - 1:
            _arrow(ax, x + width + 0.03, top + height / 2, x + width + gap - 0.03, top + height / 2)
    _box(ax, 0.2, 0.3, 5.7, 1.0, "predict.py: clasifica un archivo o un flujo (JSON)\ncon el modelo y el umbral elegidos", INK, "white", 9.2)
    _box(ax, 6.5, 0.3, 5.9, 1.0, "app/demo_app.py (Streamlit) y reports/:\ndemostración y resultados reproducibles", INK, "white", 9.2)
    _arrow(ax, centers[4], top - 0.05, 3.05, 1.35)
    _arrow(ax, centers[5], top - 0.05, 9.45, 1.35)
    ax.text(6.3, 5.2, "Arquitectura del prototipo: de los archivos crudos a la decisión", ha="center", fontsize=13, fontweight="bold")
    _save(fig, "arquitectura.png")


# ------------------------------------------------------------------ cleaning funnel


def cleaning_funnel() -> None:
    """Rows kept and removed by each cleaning step, both datasets."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
    for ax, key in zip(axes, ("unsw_nb15", "cicids2017"), strict=True):
        report = _json(config.get_dataset(key).cleaning_report_file)
        raw = report["rows_raw"]
        parts = [
            ("Flujos limpios", report["rows_final"], BLUE),
            ("Duplicados", report["rows_removed_duplicates"], ORANGE),
            ("Contradictorios", report["rows_removed_conflicting"], YELLOW),
            ("Infinitos o NaN", report["rows_removed_missing"], AQUA),
        ]
        left = 0
        for label, value, color in parts:
            ax.barh(0, value, left=left, color=color, edgecolor="white", linewidth=2, label=f"{label}: {_fmt(value)} ({100 * value / raw:.1f} %)")
            left += value
        ax.set_yticks([])
        ax.set_xlim(0, raw)
        ax.set_xlabel("Flujos")
        ax.xaxis.set_major_formatter(lambda v, _: _fmt(v))
        ax.set_title(f"{config.get_dataset(key).display_name}: {_fmt(raw)} flujos crudos")
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2, frameon=False, fontsize=9)
        ax.spines["left"].set_visible(False)
    _save(fig, "embudo_limpieza.png")


# ------------------------------------------------------------------ leakage


def leakage() -> None:
    """Share of the test set already seen in training, and the metrics it inflates."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    names = {"naive": "Ingenuo", "dedup": "Sin duplicados", "full": "Completo"}
    colors = [CRITICAL, YELLOW, BLUE]
    data = {k: _json(config.get_dataset(k).reports_dir / "leakage_ablation.json") for k in ("unsw_nb15", "cicids2017")}
    for ax, (field, title, pct) in zip(
        axes,
        [("leaked_test_share", "Prueba ya vista en entrenamiento", True), ("recall", "Recall medido", False), ("accuracy", "Accuracy medida", False)],
        strict=True,
    ):
        x = np.arange(2)
        for i, protocol in enumerate(names):
            values = [data[k][protocol][field] for k in ("unsw_nb15", "cicids2017")]
            bars = ax.bar(x + (i - 1) * 0.26, values, 0.26, color=colors[i], label=names[protocol])
            for bar, value in zip(bars, values, strict=True):
                ax.text(bar.get_x() + bar.get_width() / 2, value, f"{100 * value:.1f} %" if pct else f"{value:.3f}", ha="center", va="bottom", fontsize=8)
        ax.set_xticks(x, ["UNSW-NB15", "CICIDS2017"])
        ax.set_title(title)
        if pct:
            ax.yaxis.set_major_formatter(lambda v, _: f"{100 * v:.0f} %")
        else:
            ax.set_ylim(0.88, 1.005)
    axes[0].legend(frameon=False, fontsize=9, title="Protocolo")
    fig.suptitle("Si no se quitan los duplicados, la prueba contiene flujos que el modelo ya vio", fontweight="bold")
    _save(fig, "fuga_de_datos.png")


# ------------------------------------------------------------------ score distribution


def score_distribution() -> None:
    """Attack probability of normal and attack flows with the three thresholds (UNSW-NB15, test)."""
    dataset = config.UNSW_NB15
    scores = np.load(dataset.models_dir / "scores.npz")
    summary = _json(dataset.reports_dir / "training_summary.json")
    model = summary["best_model"]
    y, s = scores["y_test"], scores[f"{model}_test"]
    thresholds = summary["thresholds"][model]
    fig, ax = plt.subplots(figsize=(12, 5.2))
    bins = np.linspace(0, 1, 41)
    ax.hist(s[y == 0], bins=bins, color=BLUE, alpha=0.85, label=f"Normales ({_fmt((y == 0).sum())})")
    ax.hist(s[y == 1], bins=bins, color=CRITICAL, alpha=0.75, label=f"Ataques ({_fmt((y == 1).sum())})")
    ax.set_yscale("log")
    for point in POINTS:
        t = thresholds[point]
        ax.axvline(t, color=POINT_COLOR[point], lw=2.4, ls="--")
        label = POINT_NAME[point] if point == "default" else f"{POINT_NAME[point]}\numbral {t:.4f}"
        height = {"default": 0.97, "recall_target": 0.60, "fpr_budget": 0.97}[point]
        ax.text(
            t + 0.008, ax.get_ylim()[1] * 10 ** (-4 * (1 - height)), label, color=POINT_COLOR[point], fontsize=9,
            fontweight="bold", va="top", bbox={"fc": "white", "ec": "none", "alpha": 0.85, "pad": 1.5},
        )
    ax.set_xlabel("Probabilidad de ataque asignada por el modelo")
    ax.set_ylabel("Flujos de prueba (escala logarítmica)")
    ax.set_title("UNSW-NB15: los dos grupos se solapan, por eso mover el umbral solo cambia qué error se acepta")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    _save(fig, "distribucion_puntajes_unsw.png")


# ------------------------------------------------------------------ ROC with operating points


def roc_points() -> None:
    """ROC zoom with the three operating points and the project's target zone."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, key in zip(axes, ("unsw_nb15", "cicids2017"), strict=True):
        dataset = config.get_dataset(key)
        scores = np.load(dataset.models_dir / "scores.npz")
        summary = _json(dataset.reports_dir / "training_summary.json")
        model = summary["best_model"]
        y, s = scores["y_test"], scores[f"{model}_test"]
        fpr, tpr, _ = roc_curve(y, s)
        ax.plot(fpr, tpr, color=INK, lw=2)
        ax.add_patch(plt.Rectangle((0, config.RECALL_TARGET), config.FPR_TARGET, 1 - config.RECALL_TARGET, color=GOOD, alpha=0.25, label="Zona objetivo (Recall >= 0.95 y FPR <= 0.02)"))
        metrics = pd.read_csv(dataset.reports_dir / "metrics.csv")
        metrics = metrics[(metrics.model == model) & (metrics.split == "test")].set_index("operating_point")
        for point in POINTS:
            ax.scatter(metrics.loc[point, "fpr"], metrics.loc[point, "recall"], s=120, color=POINT_COLOR[point], zorder=5, edgecolor="white", linewidth=1.5, label=f"{POINT_NAME[point]}: Recall {metrics.loc[point, 'recall']:.3f}, FPR {metrics.loc[point, 'fpr']:.4f}")
        ax.set_xscale("log")
        ax.set_xlim(2e-5, 1)
        ax.set_ylim(0.5, 1.005)
        ax.set_xlabel("FPR (falsas alarmas, escala logarítmica)")
        ax.set_ylabel("Recall (ataques detectados)")
        ax.set_title(dataset.display_name)
        ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.17))
    fig.suptitle("Curva ROC del modelo ganador con los tres puntos de operación", fontweight="bold")
    _save(fig, "roc_puntos_operacion.png")


# ------------------------------------------------------------------ confusion matrices


def confusion_examples() -> None:
    """Confusion counts of the winner at the three points (UNSW-NB15, test)."""
    dataset = config.UNSW_NB15
    summary = _json(dataset.reports_dir / "training_summary.json")
    model = summary["best_model"]
    metrics = pd.read_csv(dataset.reports_dir / "metrics.csv")
    metrics = metrics[(metrics.model == model) & (metrics.split == "test")].set_index("operating_point")
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), gridspec_kw={"wspace": 0.55})
    for ax, point in zip(axes, POINTS, strict=True):
        m = metrics.loc[point]
        cells = np.array([[m.tn, m.fp], [m.fn, m.tp]])
        shares = cells / cells.sum(axis=1, keepdims=True)
        ax.imshow(shares, cmap="Blues", vmin=0, vmax=1.3)
        for i in range(2):
            for j in range(2):
                tag = [["VN", "FP"], ["FN", "VP"]][i][j]
                ax.text(j, i, f"{tag}\n{_fmt(cells[i, j])}\n({100 * shares[i, j]:.1f} % de la fila)", ha="center", va="center", fontsize=10, color="white" if shares[i, j] > 0.55 else INK)
        ax.set_xticks([0, 1], ["Predicho normal", "Predicho ataque"])
        ax.set_yticks([0, 1], ["Real normal", "Real ataque"])
        ax.set_title(f"{POINT_NAME[point]}\nRecall {m.recall:.3f}, FPR {m.fpr:.4f}", fontsize=10)
    fig.suptitle("UNSW-NB15, prueba: el mismo modelo con tres umbrales distintos", fontweight="bold", y=1.02)
    _save(fig, "matrices_confusion_unsw.png")


# ------------------------------------------------------------------ base-rate arithmetic


def alarms_per_day() -> None:
    """Why a small FPR is not small: false alarms per million normal flows."""
    rows = []
    for key in ("cicids2017", "unsw_nb15"):
        dataset = config.get_dataset(key)
        summary = _json(dataset.reports_dir / "training_summary.json")
        model = summary["best_model"]
        metrics = pd.read_csv(dataset.reports_dir / "metrics.csv")
        metrics = metrics[(metrics.model == model) & (metrics.split == "test")].set_index("operating_point")
        for point in POINTS:
            rows.append((dataset.display_name, point, float(metrics.loc[point, "fpr"])))
    fig, ax = plt.subplots(figsize=(12, 4.8))
    x = np.arange(len(rows))
    values = [1_000_000 * r[2] for r in rows]
    bars = ax.bar(x, values, color=[POINT_COLOR[r[1]] for r in rows])
    for bar, value in zip(bars, values, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value, _fmt(value), ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(x, [f"{r[0]}\n{POINT_NAME[r[1]].replace(' con ', chr(10) + 'con ')}" for r in rows], fontsize=7.5)
    ax.set_ylabel("Falsas alarmas")
    ax.set_title("Aritmética de las falsas alarmas: con un millón de flujos normales, un FPR de 0.1222 son más de cien mil alertas")
    ax.set_yscale("log")
    ax.set_ylim(10, 6e5)
    ax.text(0.01, 0.97, "Ejemplo ilustrativo: 1 000 000 de flujos normales (suposición, no un dato del proyecto)", transform=ax.transAxes, fontsize=9, va="top", color=MUTED)
    _save(fig, "alarmas_por_millon.png")


# ------------------------------------------------------------------ toy examples for the study guide


def toy_tree() -> None:
    """The decision tree fitted by sklearn on the 8-flow toy set used in the study guide."""
    from sklearn.tree import DecisionTreeClassifier, plot_tree

    flows = pd.DataFrame(
        {
            "paquetes": [2, 3, 4, 5, 60, 80, 120, 4],
            "duracion": [0.1, 0.2, 0.3, 0.2, 0.5, 0.4, 0.6, 2.5],
            "ataque": [0, 0, 0, 0, 1, 1, 1, 1],
        }
    )
    tree = DecisionTreeClassifier(max_depth=2, random_state=0, criterion="gini").fit(flows[["paquetes", "duracion"]], flows["ataque"])
    fig, ax = plt.subplots(figsize=(9, 4.6))
    plot_tree(tree, feature_names=["paquetes", "duracion"], class_names=["normal", "ataque"], filled=True, rounded=True, impurity=True, ax=ax, fontsize=10)
    ax.set_title("Árbol de decisión sobre 8 flujos de ejemplo (Gini)")
    _save(fig, "ejemplo_arbol.png")


# ------------------------------------------------------------------ slide diagrams


def ids_in_network() -> None:
    """Where a network IDS sits and what it does (schematic, no data)."""
    fig, ax = plt.subplots(figsize=(13, 5.0))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5.0)
    ax.axis("off")
    _box(ax, 0.2, 1.6, 1.8, 1.3, "Internet\n(tráfico externo)", MUTED, "white", 10)
    _box(ax, 2.6, 1.6, 1.8, 1.3, "Cortafuegos", INK, "white", 10)
    _box(ax, 5.0, 1.6, 1.8, 1.3, "Conmutador\n(copia del tráfico)", BLUE, "white", 10)
    _box(ax, 7.6, 1.6, 2.0, 1.3, "Red interna\nservidores y equipos", AQUA, "white", 10)
    _box(ax, 5.0, 3.5, 1.8, 0.9, "IDS con\naprendizaje", ORANGE, "white", 10)
    _box(ax, 10.2, 3.5, 2.6, 0.9, "Alerta al analista\n(SOC / SIEM)", CRITICAL, "white", 10)
    for x1, x2 in ((2.02, 2.58), (4.42, 4.98), (6.82, 7.58)):
        _arrow(ax, x1, 2.25, x2, 2.25)
    _arrow(ax, 5.9, 2.95, 5.9, 3.45)
    _arrow(ax, 6.82, 3.95, 10.18, 3.95)
    ax.text(5.9, 0.9, "El IDS no bloquea: observa una copia del tráfico, lo resume en flujos y decide\nsi cada flujo parece normal o un ataque. Si se equivoca hacia un lado, pasa un ataque; hacia el otro, sobran alertas.", ha="center", va="top", fontsize=9.5, color=INK)
    ax.text(6.5, 4.85, "Dónde actúa un IDS de red", ha="center", fontsize=13, fontweight="bold")
    _save(fig, "ids_en_la_red.png")


def flow_to_features() -> None:
    """One real UNSW-NB15 test flow, its features and the decision at each threshold."""
    from src.predict import classify, load_bundle

    flow = _json(ROOT / "docs" / "demo" / "flujo_ejemplo.json")
    bundle = load_bundle("unsw_nb15")
    result = classify(pd.DataFrame([flow]), bundle, "recall_target").iloc[0]
    shown = ["proto", "service", "state", "dur", "spkts", "dpkts", "sbytes", "dbytes", "sttl", "ct_state_ttl"]
    fig, ax = plt.subplots(figsize=(13, 4.8))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 4.8)
    ax.axis("off")
    ax.text(0.2, 4.45, "Un flujo de red (resumen de una conversación)", fontsize=12, fontweight="bold")
    for i, name in enumerate(shown):
        row, col = divmod(i, 5)
        x, y = 0.2 + col * 2.05, 3.0 - row * 1.25
        value = flow[name]
        text = f"{value:,.0f}".replace(",", " ") if isinstance(value, (int, float)) and abs(value) >= 1000 else (f"{value:.4g}" if isinstance(value, float) else str(value))
        ax.add_patch(FancyBboxPatch((x, y), 1.9, 0.95, boxstyle="round,pad=0.02,rounding_size=0.06", fc="#eef4fd", ec=BLUE, lw=1.2))
        ax.text(x + 0.95, y + 0.64, name, ha="center", va="center", fontsize=9, color=MUTED, family="JetBrains Mono")
        ax.text(x + 0.95, y + 0.3, text, ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(0.2, 0.55, f"... y {len(bundle['feature_columns']) - len(shown)} variables más", fontsize=9.5, color=MUTED)
    _arrow(ax, 10.5, 2.4, 11.0, 2.4)
    _box(ax, 11.05, 1.4, 1.8, 2.0, f"Modelo\n{bundle['model_name']}\n\nprobabilidad\nde ataque\n{result['attack_probability']:.4f}", ORANGE, "white", 9)
    ax.text(11.95, 0.95, result["classification"], ha="center", fontsize=11, fontweight="bold", color=CRITICAL)
    ax.text(6.5, 0.2, "Ejemplo real: primer flujo de docs/demo/flujo_ejemplo.json, tomado del conjunto de prueba.", ha="center", fontsize=8.5, color=MUTED)
    _save(fig, "flujo_a_variables.png")


def base_vs_improved() -> None:
    """The two pipelines side by side, and what each step uses (schematic)."""
    fig, ax = plt.subplots(figsize=(13, 5.2))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5.2)
    ax.axis("off")
    ax.text(6.5, 4.95, "Versión base y versión mejorada de cada modelo", ha="center", fontsize=13, fontweight="bold")
    rows = [
        (3.55, "BASE", MUTED, ["Datos de entrenamiento", "Codificar categorías", "Modelo con valores\ndel Entregable 1", "Umbral 0.5\n(los otros dos puntos se\nevalúan también)"]),
        (1.35, "MEJORADA", BLUE, ["Datos de entrenamiento", "Codificar categorías\n+ filtro de correlación", "Hiperparámetros por\nvalidación cruzada (5 folds)", "Umbral elegido\nen validación"]),
    ]
    for y, name, color, steps in rows:
        ax.text(0.15, y + 0.5, name, fontsize=11, fontweight="bold", color=color, rotation=90, va="center")
        for i, step in enumerate(steps):
            x = 0.7 + i * 3.1
            _box(ax, x, y, 2.6, 1.0, step, color, "white", 9)
            if i < len(steps) - 1:
                _arrow(ax, x + 2.62, y + 0.5, x + 3.08, y + 0.5)
    ax.text(6.5, 0.55, "Los tres puntos de operación se evalúan para las dos versiones. En ambas, el conjunto de prueba no interviene en ninguna decisión.", ha="center", fontsize=10, color=INK)
    _save(fig, "base_vs_mejorada.png")


def class_balance() -> None:
    """Flows per traffic type after cleaning, log scale, both datasets."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.4))
    for ax, key in zip(axes, ("unsw_nb15", "cicids2017"), strict=True):
        report = _json(config.get_dataset(key).cleaning_report_file)
        counts = pd.Series(report["attack_type_counts_final"]).sort_values()
        colors = [BLUE if name == config.BENIGN_LABEL else CRITICAL for name in counts.index]
        ax.barh(counts.index, counts.values, color=colors)
        for i, value in enumerate(counts.values):
            ax.text(value, i, f" {_fmt(value)}", va="center", fontsize=8)
        ax.set_xscale("log")
        ax.set_xlim(1, counts.max() * 8)
        ax.set_xlabel("Flujos limpios (escala logarítmica)")
        ax.set_title(config.get_dataset(key).display_name)
        ax.tick_params(axis="y", labelsize=8)
    fig.suptitle("Los datos están muy desbalanceados: azul, tráfico normal; rojo, familias de ataque", fontweight="bold")
    _save(fig, "desbalance_familias.png")


def main() -> int:
    for step in (architecture, cleaning_funnel, leakage, score_distribution, roc_points, confusion_examples, alarms_per_day, toy_tree, ids_in_network, flow_to_features, base_vs_improved, class_balance):
        step()
    return 0


if __name__ == "__main__":
    sys.exit(main())
