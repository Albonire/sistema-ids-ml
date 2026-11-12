"""Visual demo of the IDS prototype.

Usage (from the repository root):
    streamlit run app/demo_app.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, demo  # noqa: E402
from src.evaluate import ALGORITHM_ES, MODEL_ORDER, POINT_LABELS, pretty  # noqa: E402
from src.metrics import Metrics  # noqa: E402
from src.predict import ATTACK_TEXT, NORMAL_TEXT, classify  # noqa: E402

# Categorical slots (fixed order) and status colors of the chart palette.
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
CRITICAL, GOOD, MUTED = "#d03b3b", "#0ca30c", "#898781"
LOG_TICKS = [10**k for k in range(8)]
ALGORITHM_COLORS = {"rf": BLUE, "xgb": ORANGE, "mix": AQUA}
OUTCOME_BACKGROUND = {
    "Ataque detectado": "rgba(12, 163, 12, 0.18)",
    "Normal correcto": "rgba(12, 163, 12, 0.18)",
    "Falsa alarma": "rgba(250, 178, 25, 0.30)",
    "Ataque no detectado": "rgba(208, 59, 59, 0.25)",
}
POINT_SHORT = {
    "default": "Umbral 0.5",
    "recall_target": f"Recall >= {config.RECALL_TARGET}",
    "fpr_budget": f"FPR <= {config.FPR_TARGET}",
}


def fmt_int(value: float) -> str:
    return f"{int(value):,}".replace(",", ".")


def fmt_pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f} %".replace(".", ",")


@st.cache_resource(show_spinner="Cargando modelo y resultados...")
def get_context(dataset_key: str) -> demo.DemoContext:
    return demo.load_demo_context(dataset_key)


def show_missing(dataset_key: str) -> None:
    name = config.get_dataset(dataset_key).display_name
    st.warning(f"Faltan los resultados de {name} en este computador. Generarlos con:")
    st.code(
        "\n".join(
            [
                f"python -m src.download_data --dataset {dataset_key}",
                f"python -m src.preprocess --dataset {dataset_key}",
                f"python -m src.train --dataset {dataset_key}",
                f"python -m src.leakage_ablation --dataset {dataset_key}",
                f"python -m src.evaluate --dataset {dataset_key}",
            ]
        ),
        language="bash",
    )


def criterion_banner(metrics: Metrics) -> None:
    text = (
        f"Recall {metrics.recall:.4f} (meta >= {config.RECALL_TARGET}) y "
        f"FPR {metrics.fpr:.5f} (meta <= {config.FPR_TARGET})"
    )
    if demo.meets_criterion(metrics):
        st.success(f"Cumple el criterio del proyecto: {text}")
    else:
        st.error(f"No cumple el criterio del proyecto: {text}")


def metric_row(metrics: Metrics) -> None:
    columns = st.columns(5)
    columns[0].metric("Recall (detección)", f"{metrics.recall:.4f}")
    columns[1].metric("FPR (falsas alarmas)", f"{metrics.fpr:.5f}")
    columns[2].metric("Precisión", f"{metrics.precision:.4f}")
    columns[3].metric("Ataques no detectados", fmt_int(metrics.fn))
    columns[4].metric("Falsas alarmas", fmt_int(metrics.fp))


# ---------------------------------------------------------------- tab 1: data


def tab_data(context: demo.DemoContext) -> None:
    report = context.cleaning
    if report is None:
        st.info("No hay reporte de limpieza. Ejecutar `python -m src.preprocess`.")
        return
    removed = report["rows_raw"] - report["rows_final"]
    columns = st.columns(4)
    columns[0].metric("Flujos crudos", fmt_int(report["rows_raw"]))
    columns[1].metric("Flujos limpios", fmt_int(report["rows_final"]))
    columns[2].metric("Eliminados", fmt_pct(removed / report["rows_raw"]))
    columns[3].metric("Variables", report["n_features"])

    st.subheader("Qué pasa con cada flujo crudo")
    funnel = demo.cleaning_funnel(report)
    funnel["label"] = [
        f"{step}: {fmt_int(rows)} ({fmt_pct(share)})"
        for step, rows, share in zip(funnel["step"], funnel["rows"], funnel["share"])
    ]
    order = ["Flujos limpios", "Duplicados", "Infinitos o NaN", "Contradictorios"]
    funnel["order"] = funnel["step"].map(order.index)
    bar = (
        alt.Chart(funnel)
        .mark_bar(height=56, stroke="white", strokeWidth=2)
        .encode(
            x=alt.X("rows:Q", stack="zero", axis=None),
            color=alt.Color(
                "step:N",
                scale=alt.Scale(domain=order, range=[BLUE, ORANGE, AQUA, YELLOW]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            order="order:Q",
            tooltip=[alt.Tooltip("label:N", title="Paso")],
        )
        .properties(height=110)
    )
    st.altair_chart(bar, width="stretch")
    for label in funnel.sort_values("order")["label"]:
        name, _, detail = label.partition(":")
        st.markdown(f"**{name}**:{detail}")
    st.caption(
        "Los duplicados se quitan antes de partir los datos: si quedaran, el mismo vector "
        "estaría en entrenamiento y en prueba, y las métricas saldrían infladas."
    )

    st.subheader("Flujos limpios por tipo de tráfico")
    counts = (
        pd.Series(report["attack_type_counts_final"], name="rows")
        .rename_axis("family")
        .reset_index()
        .sort_values("rows", ascending=False)
    )
    counts["kind"] = counts["family"].map(
        lambda f: "Normal" if f == config.BENIGN_LABEL else "Ataque"
    )
    families = (
        alt.Chart(counts)
        .mark_bar(cornerRadiusEnd=4, height=14)
        .encode(
            y=alt.Y("family:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
            x=alt.X(
                "rows:Q",
                title="Flujos (escala logarítmica)",
                stack=None,
                scale=alt.Scale(type="log", domainMin=1, nice=True),
                axis=alt.Axis(values=LOG_TICKS, format="~s"),
            ),
            x2=alt.datum(1),
            color=alt.Color(
                "kind:N",
                scale=alt.Scale(domain=["Normal", "Ataque"], range=[MUTED, BLUE]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("family:N", title="Tipo"),
                alt.Tooltip("rows:Q", title="Flujos", format=","),
            ],
        )
        .properties(height=alt.Step(24))
    )
    st.altair_chart(families, width="stretch")


# ------------------------------------------------------- tab 2: live classify


def read_flows(context: demo.DemoContext) -> pd.DataFrame | None:
    key = context.dataset.key
    source = st.radio(
        "Origen de los flujos",
        ["Ejemplos del conjunto de prueba", "Subir un CSV", "Un flujo en JSON"],
        horizontal=True,
        key=f"source_{key}",
    )
    if source == "Subir un CSV":
        uploaded = st.file_uploader("CSV con un flujo por fila", type="csv", key=f"upload_{key}")
        if uploaded is None:
            return None
        return pd.read_csv(uploaded, encoding="utf-8-sig", skipinitialspace=True)
    example_file = demo.EXAMPLE_FILES[key]
    if not example_file.is_file():
        st.info(
            f"No existe `{example_file.name}`. Generarlo con "
            f"`python -m src.demo --dataset {key} --write-examples`."
        )
        return None
    examples = pd.read_csv(example_file)
    if source == "Un flujo en JSON":
        first = examples[context.bundle["feature_columns"]].iloc[len(examples) // 2]
        text = st.text_area(
            "Flujo (objeto JSON con las variables del modelo)",
            value=json.dumps(json.loads(first.to_json()), indent=1),
            height=260,
            key=f"json_{key}",
        )
        try:
            return pd.DataFrame([json.loads(text)])
        except json.JSONDecodeError as error:
            st.error(f"JSON inválido: {error}")
            return None
    return examples


def tab_classify(context: demo.DemoContext, point: str) -> None:
    threshold = float(context.bundle["thresholds"][point])
    st.markdown(
        f"Modelo **{pretty(context.bundle['model_name'])}**, punto de operación "
        f"**{POINT_SHORT[point]}** (umbral {threshold:.4f}). Un flujo se marca como ataque "
        "cuando su probabilidad supera el umbral."
    )
    flows = read_flows(context)
    if flows is None:
        return
    try:
        predictions = classify(flows, context.bundle, point)
    except ValueError as error:
        st.error(f"No se pudo clasificar: {error}")
        return
    result = demo.judge(predictions, flows)
    result.insert(0, "flujo", [f"Flujo {i}" for i in range(len(result))])

    attacks = int(result["prediction"].sum())
    columns = st.columns(4)
    columns[0].metric("Flujos analizados", fmt_int(len(result)))
    columns[1].metric(ATTACK_TEXT, fmt_int(attacks))
    columns[2].metric(NORMAL_TEXT, fmt_int(len(result) - attacks))
    if "correct" in result:
        columns[3].metric("Aciertos", f"{int(result['correct'].sum())} de {len(result)}")

    shown = result.head(200)
    if len(result) > len(shown):
        st.caption(f"Se muestran los primeros {len(shown)} flujos de {fmt_int(len(result))}.")
    bars = (
        alt.Chart(shown)
        .mark_bar(cornerRadiusEnd=4, height=14)
        .encode(
            y=alt.Y("flujo:N", sort=None, title=None),
            x=alt.X(
                "attack_probability:Q",
                title="Probabilidad de ataque",
                scale=alt.Scale(domain=[0, 1]),
            ),
            color=alt.Color(
                "classification:N",
                scale=alt.Scale(domain=[ATTACK_TEXT, NORMAL_TEXT], range=[CRITICAL, MUTED]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("flujo:N", title="Flujo"),
                alt.Tooltip("attack_probability:Q", title="Probabilidad", format=".4f"),
                alt.Tooltip("classification:N", title="Decisión"),
            ]
            + ([alt.Tooltip("real:N", title="Tipo real")] if "real" in shown else []),
        )
    )
    rule_data = pd.DataFrame({"threshold": [threshold], "text": [f"umbral {threshold:.3f}"]})
    rule = alt.Chart(rule_data).mark_rule(strokeDash=[4, 4], size=2, color=MUTED).encode(x="threshold:Q")
    rule_label = (
        alt.Chart(rule_data)
        .mark_text(align="left", dx=5, dy=-4, baseline="bottom", color=MUTED, fontSize=12)
        .encode(x="threshold:Q", y=alt.value(0), text="text:N")
    )
    chart = (bars + rule + rule_label).properties(height=alt.Step(24))
    st.altair_chart(chart, width="stretch")

    table = shown.rename(
        columns={
            "classification": "decisión",
            "attack_probability": "probabilidad",
            "real": "tipo real",
            "outcome": "resultado",
        }
    ).drop(columns=["prediction", "correct"], errors="ignore")
    if demo.NOTE_COLUMN in flows.columns:
        table[demo.NOTE_COLUMN] = flows[demo.NOTE_COLUMN].head(len(table)).to_numpy()
    styler = table.style.format({"probabilidad": "{:.4f}"})
    if "resultado" in table:
        styler = styler.map(
            lambda value: f"background-color: {OUTCOME_BACKGROUND.get(value, 'transparent')}",
            subset=["resultado"],
        )
    st.dataframe(styler, width="stretch", hide_index=True)


# ------------------------------------------------- tab 3: interactive threshold


def confusion_chart(metrics: Metrics) -> alt.Chart:
    cells = pd.DataFrame(
        [
            ("Real: ataque", "Predicho: ataque", metrics.tp, metrics.recall, "Ataques detectados"),
            ("Real: ataque", "Predicho: normal", metrics.fn, 1 - metrics.recall, "Ataques no detectados"),
            ("Real: normal", "Predicho: ataque", metrics.fp, metrics.fpr, "Falsas alarmas"),
            ("Real: normal", "Predicho: normal", metrics.tn, 1 - metrics.fpr, "Normales correctos"),
        ],
        columns=["real", "predicted", "count", "share", "meaning"],
    )
    cells["count_text"] = cells["count"].map(fmt_int)
    cells["share_text"] = cells["share"].map(fmt_pct)
    base = alt.Chart(cells).encode(
        x=alt.X(
            "predicted:N",
            title=None,
            sort=["Predicho: ataque", "Predicho: normal"],
            axis=alt.Axis(orient="top", labelAngle=0),
        ),
        y=alt.Y("real:N", title=None, sort=["Real: ataque", "Real: normal"]),
    )
    heat = base.mark_rect(stroke="white", strokeWidth=2).encode(
        color=alt.Color(
            "share:Q",
            scale=alt.Scale(domain=[0, 1], range=["#cde2fb", "#0d366b"]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("meaning:N", title="Celda"),
            alt.Tooltip("count:Q", title="Flujos", format=","),
            alt.Tooltip("share:Q", title="Proporción de la fila", format=".2%"),
        ],
    )
    ink = alt.condition(alt.datum.share > 0.55, alt.value("white"), alt.value("black"))
    count = base.mark_text(fontSize=20, fontWeight="bold", dy=-10).encode(text="count_text:N", color=ink)
    share = base.mark_text(fontSize=14, dy=14).encode(text="share_text:N", color=ink)
    return (heat + count + share).properties(height=260)


def roc_chart(
    context: demo.DemoContext, model: str, current: Metrics, zoom: bool
) -> alt.LayerChart:
    points = {
        name: demo.metrics_at_threshold(context.scores, model, threshold)
        for name, threshold in context.summary["thresholds"][model].items()
    }
    limit, floor = 1.0, 0.0
    if zoom:
        # Frame the working region: every stored point, the chosen one and the target zone.
        shown = [*points.values(), current]
        limit = min(1.0, max(2.5 * config.FPR_TARGET, 1.6 * max(m.fpr for m in shown)))
        floor = max(0.0, min(0.9, min(m.recall for m in shown) - 0.1))
    curve = demo.roc_points(context.scores, model, max_points=4000)
    curve = curve[(curve["fpr"] <= limit) & (curve["recall"] >= floor)]
    x = alt.X("fpr:Q", title="FPR (tasa de falsas alarmas)", scale=alt.Scale(domain=[0, limit]))
    y = alt.Y(
        "recall:Q", title="Recall (ataques detectados)", scale=alt.Scale(domain=[floor, 1], zero=False)
    )
    target = (
        alt.Chart(
            pd.DataFrame(
                {"x": [0.0], "x2": [config.FPR_TARGET], "y": [config.RECALL_TARGET], "y2": [1.0]}
            )
        )
        .mark_rect(color=GOOD, opacity=0.25)
        .encode(x="x:Q", x2="x2:Q", y="y:Q", y2="y2:Q")
    )
    line = (
        alt.Chart(curve)
        .mark_line(color=BLUE, strokeWidth=2)
        .encode(
            x=x,
            y=y,
            tooltip=[
                alt.Tooltip("threshold:Q", title="Umbral", format=".3f"),
                alt.Tooltip("recall:Q", title="Recall", format=".4f"),
                alt.Tooltip("fpr:Q", title="FPR", format=".4f"),
            ],
        )
    )
    stored = pd.DataFrame(
        [
            {
                "label": POINT_SHORT[point],
                "fpr": points[point].fpr,
                "recall": points[point].recall,
                "threshold": threshold,
            }
            for point, threshold in context.summary["thresholds"][model].items()
        ]
    )
    tooltip = [
        alt.Tooltip("label:N", title="Punto"),
        alt.Tooltip("threshold:Q", title="Umbral", format=".4f"),
        alt.Tooltip("recall:Q", title="Recall", format=".4f"),
        alt.Tooltip("fpr:Q", title="FPR", format=".4f"),
    ]
    stored_points = (
        alt.Chart(stored)
        .mark_point(size=90, filled=True, color=BLUE, stroke="white", strokeWidth=2, opacity=1)
        .encode(x="fpr:Q", y="recall:Q", tooltip=tooltip)
    )
    stored_labels = (
        alt.Chart(stored)
        .mark_text(align="left", dx=9, dy=12, color=MUTED, fontSize=12)
        .encode(x="fpr:Q", y="recall:Q", text="label:N")
    )
    now = pd.DataFrame(
        [
            {
                "label": "Umbral elegido",
                "fpr": current.fpr,
                "recall": current.recall,
                "threshold": current.threshold,
            }
        ]
    )
    now = now[(now["fpr"] <= limit) & (now["recall"] >= floor)]
    current_point = (
        alt.Chart(now)
        .mark_point(
            size=220, filled=True, color=ORANGE, stroke="white", strokeWidth=2, opacity=1,
            shape="diamond",
        )
        .encode(x="fpr:Q", y="recall:Q", tooltip=tooltip)
    )
    return (target + line + stored_points + stored_labels + current_point).properties(height=360)


def family_chart(table: pd.DataFrame) -> alt.Chart:
    attacks = table[table["family"] != config.BENIGN_LABEL].copy()
    attacks["label"] = [f"{family} (n={fmt_int(n)})" for family, n in zip(attacks["family"], attacks["n"])]
    bars = (
        alt.Chart(attacks)
        .mark_bar(cornerRadiusEnd=4, height=14, color=BLUE)
        .encode(
            y=alt.Y("label:N", sort="x", title=None, axis=alt.Axis(labelLimit=260)),
            x=alt.X("flagged_share:Q", title="Tasa de detección", scale=alt.Scale(domain=[0, 1])),
            tooltip=[
                alt.Tooltip("family:N", title="Familia"),
                alt.Tooltip("flagged_share:Q", title="Detección", format=".2%"),
                alt.Tooltip("n:Q", title="Flujos de prueba", format=","),
            ],
        )
    )
    return bars.properties(height=alt.Step(24))


def tab_threshold(context: demo.DemoContext, point: str) -> None:
    key = context.dataset.key
    left, right = st.columns([1, 2])
    model = left.selectbox(
        "Modelo",
        MODEL_ORDER,
        index=MODEL_ORDER.index(context.best_model),
        format_func=pretty,
        key=f"threshold_model_{key}",
    )
    stored = context.summary["thresholds"][model]
    threshold = right.slider(
        "Umbral de decisión (probabilidad mínima para marcar un ataque)",
        min_value=0.0,
        max_value=1.0,
        value=float(round(stored[point], 4)),
        step=0.0001,
        format="%.4f",
        key=f"threshold_{key}_{model}_{point}",
    )
    st.caption(
        "Umbrales guardados (elegidos en validación): "
        + ", ".join(f"{POINT_SHORT[p]} = {t:.4f}" for p, t in stored.items())
        + ". Las cifras de abajo son del conjunto de prueba."
    )
    metrics = demo.metrics_at_threshold(context.scores, model, threshold)
    metric_row(metrics)
    criterion_banner(metrics)

    left, right = st.columns(2)
    with left:
        st.subheader("Matriz de confusión")
        st.altair_chart(confusion_chart(metrics), width="stretch")
    with right:
        st.subheader("Curva ROC")
        zoom = st.toggle("Acercar a la zona de trabajo", value=True, key=f"zoom_{key}")
        st.altair_chart(roc_chart(context, model, metrics, zoom), width="stretch")
        st.caption(
            "Rombo naranja: umbral elegido. Puntos azules: umbrales guardados. "
            "Zona verde: meta del proyecto (Recall >= 0.95 y FPR <= 0.02)."
        )

    st.subheader("Detección por familia de ataque con este umbral")
    st.altair_chart(
        family_chart(demo.family_detection(context.scores, model, threshold)), width="stretch"
    )


# ------------------------------------------------------ tab 4: model comparison


def tab_models(context: demo.DemoContext, point: str) -> None:
    comparison = demo.model_comparison(context.metrics)
    at_point = comparison[comparison["operating_point"] == point].copy()
    at_point["algorithm_label"] = at_point["algorithm"].map(ALGORITHM_ES)
    at_point["variant_label"] = at_point["variant"].map({"baseline": "Base", "improved": "Mejorado"})
    st.markdown(
        f"Los seis modelos en el conjunto de prueba, punto de operación "
        f"**{POINT_LABELS[point]}**. Mejor modelo elegido en validación: "
        f"**{pretty(context.best_model)}**."
    )

    left, right = st.columns([3, 2])
    with left:
        st.subheader("Falsas alarmas frente a detección")
        pad_x = max(float(at_point["fpr"].max() - at_point["fpr"].min()) * 0.25, 1e-5)
        pad_y = max(float(at_point["recall"].max() - at_point["recall"].min()) * 0.25, 1e-4)
        x_domain = [max(0.0, at_point["fpr"].min() - pad_x), at_point["fpr"].max() + pad_x]
        y_domain = [at_point["recall"].min() - pad_y, min(1.0, at_point["recall"].max() + pad_y)]
        algorithms = list(ALGORITHM_ES.values())
        points = (
            alt.Chart(at_point)
            .mark_point(size=160, filled=True, opacity=1, stroke="white", strokeWidth=2)
            .encode(
                x=alt.X("fpr:Q", title="FPR (menor es mejor)", scale=alt.Scale(domain=x_domain)),
                y=alt.Y("recall:Q", title="Recall (mayor es mejor)", scale=alt.Scale(domain=y_domain)),
                color=alt.Color(
                    "algorithm_label:N",
                    scale=alt.Scale(domain=algorithms, range=list(ALGORITHM_COLORS.values())),
                    legend=alt.Legend(title="Algoritmo", orient="top"),
                ),
                shape=alt.Shape(
                    "variant_label:N",
                    scale=alt.Scale(domain=["Base", "Mejorado"], range=["circle", "diamond"]),
                    legend=alt.Legend(title="Versión", orient="top"),
                ),
                tooltip=[
                    alt.Tooltip("model_label:N", title="Modelo"),
                    alt.Tooltip("recall:Q", title="Recall", format=".4f"),
                    alt.Tooltip("fpr:Q", title="FPR", format=".5f"),
                    alt.Tooltip("fn:Q", title="Ataques no detectados", format=","),
                    alt.Tooltip("fp:Q", title="Falsas alarmas", format=","),
                ],
            )
        )
        labels = (
            alt.Chart(at_point)
            .mark_text(align="left", dx=10, dy=-8, fontSize=12, color=MUTED)
            .encode(x="fpr:Q", y="recall:Q", text="model_label:N")
        )
        st.altair_chart((points + labels).properties(height=380), width="stretch")
        st.caption("Los ejes están acercados: las diferencias entre modelos son pequeñas.")
    with right:
        st.subheader("Variables más importantes")
        importances = (
            pd.Series(context.summary["feature_importances"]["xgb_improved"], name="importance")
            .rename_axis("feature")
            .reset_index()
            .head(10)
        )
        bars = (
            alt.Chart(importances)
            .mark_bar(cornerRadiusEnd=4, height=14, color=ORANGE)
            .encode(
                y=alt.Y("feature:N", sort="-x", title=None, axis=alt.Axis(labelLimit=220)),
                x=alt.X("importance:Q", title="Importancia en XGBoost (mejorado)"),
                tooltip=[
                    alt.Tooltip("feature:N", title="Variable"),
                    alt.Tooltip("importance:Q", title="Importancia", format=".3f"),
                ],
            )
            .properties(height=380)
        )
        st.altair_chart(bars, width="stretch")

    st.subheader("Tabla de métricas (prueba)")
    table = at_point[
        ["model_label", "recall", "fpr", "precision", "f1", "accuracy", "roc_auc", "fn", "fp", "threshold"]
    ].rename(
        columns={
            "model_label": "modelo",
            "precision": "precisión",
            "fn": "ataques no detectados",
            "fp": "falsas alarmas",
            "threshold": "umbral",
        }
    )
    st.dataframe(
        table.style.format(
            {c: "{:.4f}" for c in ["recall", "precisión", "f1", "accuracy", "roc_auc", "umbral"]}
            | {"fpr": "{:.5f}"}
        ),
        width="stretch",
        hide_index=True,
    )

    st.subheader(f"Detección por familia: {pretty(context.best_model)}")
    families = demo.family_table(context).rename_axis("familia").reset_index()
    families = families.rename(columns={**POINT_SHORT, "n": "flujos de prueba"})
    st.dataframe(
        families,
        width="stretch",
        height=35 * (len(families) + 1) + 3,
        hide_index=True,
        column_config={
            label: st.column_config.ProgressColumn(label, min_value=0.0, max_value=1.0, format="%.3f")
            for label in POINT_SHORT.values()
        },
    )
    st.caption(
        f"En la fila {config.BENIGN_LABEL} el valor es la tasa de falsas alarmas; "
        "en las demás, la tasa de detección."
    )


# ---------------------------------------------------------- tab 5: data leakage


def tab_leakage(context: demo.DemoContext) -> None:
    ablation = context.ablation
    if ablation is None:
        st.info(
            "No hay ablación guardada. Ejecutar "
            f"`python -m src.leakage_ablation --dataset {context.dataset.key}`."
        )
        return
    names = {
        "naive": "Ingenuo (solo inf/NaN)",
        "dedup": "Sin duplicados",
        "full": "Completo (proyecto)",
    }
    frame = pd.DataFrame(
        [{"protocol": names[key], **values} for key, values in ablation.items() if key in names]
    )
    naive, full = ablation["naive"], ablation["full"]
    st.markdown(
        "El mismo XGBoost base entrenado con tres protocolos de limpieza. Si no se quitan "
        "los duplicados, parte de la prueba son vectores que el modelo ya vio al entrenar."
    )
    columns = st.columns(3)
    columns[0].metric("Prueba ya vista (ingenuo)", fmt_pct(naive["leaked_test_share"]))
    columns[1].metric(
        "Recall ingenuo frente a completo",
        f"{naive['recall']:.4f}",
        delta=f"{100 * (naive['recall'] - full['recall']):+.1f} puntos",
        delta_color="off",
    )
    columns[2].metric(
        "Accuracy ingenua frente a completa",
        f"{naive['accuracy']:.4f}",
        delta=f"{100 * (naive['accuracy'] - full['accuracy']):+.1f} puntos",
        delta_color="off",
    )

    order = list(names.values())

    def protocol_bars(field: str, title: str, fmt: str, zero: bool) -> alt.LayerChart:
        base = alt.Chart(frame).encode(
            y=alt.Y("protocol:N", sort=order, title=None, axis=alt.Axis(labelLimit=200)),
            x=alt.X(f"{field}:Q", title=title, scale=alt.Scale(zero=zero, nice=True)),
        )
        bars = base.mark_bar(cornerRadiusEnd=4, height=22, color=BLUE).encode(
            tooltip=[
                alt.Tooltip("protocol:N", title="Protocolo"),
                alt.Tooltip(f"{field}:Q", title=title, format=fmt),
                alt.Tooltip("rows:Q", title="Filas", format=","),
            ]
        )
        text = base.mark_text(align="left", dx=5, color=MUTED, fontSize=12).encode(text=alt.Text(f"{field}:Q", format=fmt))
        return (bars + text).properties(height=150)

    left, right = st.columns(2)
    with left:
        st.subheader("Prueba con vector repetido en entrenamiento")
        st.altair_chart(
            protocol_bars("leaked_test_share", "Proporción de la prueba", ".1%", True),
            width="stretch",
        )
    with right:
        st.subheader("Recall medido en prueba")
        st.altair_chart(protocol_bars("recall", "Recall", ".4f", True), width="stretch")

    table = frame.rename(
        columns={
            "protocol": "protocolo",
            "rows": "filas",
            "test_rows": "filas de prueba",
            "leaked_test_share": "prueba repetida",
        }
    )
    st.dataframe(
        table.style.format(
            {"prueba repetida": "{:.2%}", "accuracy": "{:.4f}", "recall": "{:.4f}",
             "fpr": "{:.5f}", "f1": "{:.4f}"}
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption("Una sola semilla y un solo modelo: es evidencia de magnitud, no una prueba estadística.")


# ------------------------------------------------------------------------ main


def sidebar() -> tuple[str, str]:
    st.sidebar.title("IDS con Machine Learning")
    st.sidebar.caption("Seguridad Informática, Entregable 2")
    keys = ["unsw_nb15", "cicids2017"]
    dataset_key = st.sidebar.radio(
        "Dataset", keys, format_func=lambda k: config.get_dataset(k).display_name
    )
    point = st.sidebar.radio(
        "Punto de operación",
        list(POINT_SHORT),
        index=1,
        format_func=lambda p: POINT_LABELS[p][0].upper() + POINT_LABELS[p][1:],
    )
    return dataset_key, point


def sidebar_summary(context: demo.DemoContext, point: str) -> None:
    sizes: dict[str, Any] = context.summary["split_sizes"]
    st.sidebar.divider()
    st.sidebar.markdown(f"**Modelo ganador**  \n{pretty(context.best_model)}")
    st.sidebar.markdown(
        "**Umbrales**  \n"
        + "  \n".join(
            f"{'**' if p == point else ''}{POINT_SHORT[p]}: {t:.4f}{'**' if p == point else ''}"
            for p, t in context.bundle["thresholds"].items()
        )
    )
    st.sidebar.markdown(
        "**Partición 70/15/15**  \n"
        f"Entrenamiento: {fmt_int(sizes['train'])}  \n"
        f"Validación: {fmt_int(sizes['val'])}  \n"
        f"Prueba: {fmt_int(sizes['test'])}"
    )
    st.sidebar.caption(
        f"Criterio del proyecto: Recall >= {config.RECALL_TARGET} y FPR <= {config.FPR_TARGET}."
    )


def main() -> None:
    st.set_page_config(page_title="Demo IDS", layout="wide")
    dataset_key, point = sidebar()
    st.title("Sistema de detección de intrusiones")
    st.caption(
        "¿Qué algoritmo ofrece el mejor equilibrio entre capacidad de detección y tasa de "
        "falsos positivos?"
    )
    if demo.missing_artifacts(dataset_key):
        show_missing(dataset_key)
        return
    context = get_context(dataset_key)
    sidebar_summary(context, point)

    data, live, threshold, models, leakage = st.tabs(
        ["1. Datos", "2. Clasificar en vivo", "3. Umbral interactivo", "4. Comparación de modelos", "5. Fuga de datos"]
    )
    with data:
        tab_data(context)
    with live:
        tab_classify(context, point)
    with threshold:
        tab_threshold(context, point)
    with models:
        tab_models(context, point)
    with leakage:
        tab_leakage(context)


main()
