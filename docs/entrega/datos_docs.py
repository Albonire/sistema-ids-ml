"""Numbers and tables for the delivery documents, read from the pipeline outputs.

The markdown sources use `{{key}}` for an inline number and `{{>table arg ...}}` for a table.
Nothing is typed by hand: an unknown key or table raises an error, so a typo cannot slip in
as a made-up figure. Number convention: decimal point; thousands separated by a no-break space.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src import config  # noqa: E402
from src.evaluate import MODEL_ORDER, detection_by_attack_type, pretty  # noqa: E402
from src.experiments import PAIRS  # noqa: E402
from src.train import OPERATING_POINTS  # noqa: E402

NB = " "
DATASETS = {"unsw": "unsw_nb15", "cic": "cicids2017"}
PROBABILITY_METRICS = ("recall", "precision", "f1", "accuracy", "roc_auc", "pr_auc", "fpr", "leaked_test_share")
COUNT_METRICS = ("tp", "tn", "fp", "fn", "n_train", "n_test", "rows", "test_rows")
POINT_TEXT = {
    "default": "umbral 0.5",
    "recall_target": "mínimo FPR con Recall >= 0.95",
    "fpr_budget": "máximo Recall con FPR <= 0.02",
}
PROTOCOL_TEXT = {
    "A_oficial_ingenuo": "A. Particiones oficiales sin depurar",
    "B_oficial_depurado": "B. Particiones oficiales depuradas",
    "C_cv5_ingenuo": "C1. Validación cruzada 5 folds, sin depurar",
    "C_cv5_depurado": "C2. Validación cruzada 5 folds, depurada",
}


def slug(text: str) -> str:
    """ASCII key fragment for a free-text label."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower().replace("ñ", "n")).strip("_")


def fi(value: float) -> str:
    return f"{int(round(value)):,}".replace(",", NB)


def ff(value: float, digits: int = 4) -> str:
    return f"{value:.{digits}f}"


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}{NB}%"


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _put_metric(N: dict[str, str], prefix: str, metric: str, value: float) -> None:
    if metric in COUNT_METRICS:
        N[f"{prefix}.{metric}"] = fi(value)
        return
    N[f"{prefix}.{metric}"] = ff(value, 4)
    if metric in PROBABILITY_METRICS:
        N[f"{prefix}.{metric}5"] = ff(value, 5)
        N[f"{prefix}.{metric}_pct"] = pct(value, 1)
        N[f"{prefix}.{metric}_pct2"] = pct(value, 2)


def collect() -> dict[str, str]:
    """Flat dictionary of every number the documents may use."""
    N: dict[str, str] = {}
    for short, key in DATASETS.items():
        ds = config.get_dataset(key)
        clean = _json(ds.cleaning_report_file)
        raw, final = clean["rows_raw"], clean["rows_final"]
        for k in (
            "rows_raw", "rows_with_infinite", "rows_removed_missing", "rows_removed_duplicates",
            "rows_removed_conflicting", "rows_final", "n_features",
        ):
            N[f"{short}.clean.{k}"] = fi(clean[k])
        N[f"{short}.clean.removed"] = fi(raw - final)
        N[f"{short}.clean.removed_pct"] = pct((raw - final) / raw)
        N[f"{short}.clean.dup_pct"] = pct(clean["rows_removed_duplicates"] / raw)
        N[f"{short}.clean.conf_pct"] = pct(clean["rows_removed_conflicting"] / raw, 2)
        N[f"{short}.clean.final_pct"] = pct(final / raw)
        N[f"{short}.clean.constant"] = str(len(clean["constant_columns_dropped"]))
        normal, attack = clean["binary_counts_final"]["0"], clean["binary_counts_final"]["1"]
        N[f"{short}.clean.normal"], N[f"{short}.clean.attack"] = fi(normal), fi(attack)
        N[f"{short}.clean.normal_pct"], N[f"{short}.clean.attack_pct"] = pct(normal / final), pct(attack / final)
        for fam, n in clean["attack_type_counts_final"].items():
            N[f"{short}.fam.{slug(fam)}"] = fi(n)
        for fam, n in clean["attack_type_counts_raw"].items():
            N[f"{short}.famraw.{slug(fam)}"] = fi(n)

        summary = _json(ds.reports_dir / "training_summary.json")
        for part, n in summary["split_sizes"].items():
            N[f"{short}.split.{part}"] = fi(n)
        N[f"{short}.best"] = pretty(summary["best_model"])
        N[f"{short}.best_key"] = summary["best_model"]
        N[f"{short}.best_budget"] = pretty(summary["best_model_fpr_budget"])
        for model, thresholds in summary["thresholds"].items():
            for point, t in thresholds.items():
                N[f"{short}.thr.{model}.{point}"] = ff(t, 4)
        for model, info in summary["models"].items():
            N[f"{short}.fit.{model}"] = fi(info["fit_seconds"])
            if info.get("cv_average_precision") is not None:
                N[f"{short}.cvap.{model}"] = ff(info["cv_average_precision"], 4)
        N[f"{short}.filter.dropped"] = str(len(summary["features_dropped_by_filter"]["xgb_improved"]))
        for i, (name, value) in enumerate(summary["feature_importances"]["xgb_improved"].items()):
            N[f"{short}.imp.{i + 1}.name"], N[f"{short}.imp.{i + 1}.value"] = name, ff(value, 3)

        metrics = pd.read_csv(ds.reports_dir / "metrics.csv")
        for _, row in metrics.iterrows():
            tag = "m" if row["split"] == "test" else "v"
            for metric in (*PROBABILITY_METRICS[:-1], "tp", "tn", "fp", "fn", "threshold"):
                _put_metric(N, f"{short}.{tag}.{row['model']}.{row['operating_point']}", metric, float(row[metric]))

        seeds_path = ds.reports_dir / "multiseed_summary.csv"
        if seeds_path.is_file():
            seeds = pd.read_csv(seeds_path)
            info = _json(ds.reports_dir / "multiseed_summary.json")
            N[f"{short}.s.n"] = str(len(info["seeds"]))
            for _, row in seeds.iterrows():
                base = f"{short}.s.{row['model']}.{row['operating_point']}"
                for metric in ("recall", "fpr", "precision", "f1", "accuracy", "roc_auc", "fn", "fp"):
                    for stat in ("mean", "std", "min", "max"):
                        value = float(row[f"{metric}_{stat}"])
                        N[f"{base}.{metric}_{stat}"] = fi(value) if metric in ("fn", "fp") else ff(value, 4)
                        if metric == "fpr":
                            N[f"{base}.fpr5_{stat}"] = ff(value, 5)
            for rule in ("recall_target", "fpr_budget"):
                names = [v[rule] for v in info["best_by_seed"].values()]
                for model in MODEL_ORDER:
                    N[f"{short}.s.wins.{rule}.{model}"] = str(names.count(model))
            repro = info.get("primary_reproduction")
            if repro:
                N[f"{short}.s.repro"] = f"{repro['max_abs_difference']:.1e}"

        diff_path = ds.reports_dir / "multiseed_differences.csv"
        if diff_path.is_file():
            for _, row in pd.read_csv(diff_path).iterrows():
                base = f"{short}.sd.{row['algorithm']}.{row['operating_point']}.{row['metric']}"
                digits = 5 if row["metric"] == "fpr" else 4
                N[f"{base}.mean"] = f"{row['mean_difference']:+.{digits}f}"
                N[f"{base}.std"] = f"{row['std_difference']:.{digits}f}"
                N[f"{base}.better"] = str(int(row["seeds_better"]))
                N[f"{short}.sd.n"] = str(int(row["n_seeds"]))

        pair_path = ds.reports_dir / "pairwise_tests.csv"
        if pair_path.is_file():
            for _, row in pd.read_csv(pair_path).iterrows():
                base = f"{short}.p.{row['model_a']}__{row['model_b']}.{row['operating_point']}.{row['metric']}"
                digits = 5 if row["metric"] == "fpr" else 4
                N[f"{base}.diff"] = f"{row['difference']:+.{digits}f}"
                N[f"{base}.low"], N[f"{base}.high"] = f"{row['low']:+.{digits}f}", f"{row['high']:+.{digits}f}"
                N[f"{base}.p"] = f"{row['p_value']:.3f}"

        abl_path = ds.reports_dir / "feature_ablation.csv"
        if abl_path.is_file():
            for _, row in pd.read_csv(abl_path).iterrows():
                base = f"{short}.a.{slug(row['group'])}.{row['operating_point']}"
                for metric in ("recall", "fpr", "accuracy", "roc_auc"):
                    N[f"{base}.{metric}"] = ff(float(row[metric]), 4)

        leak_path = ds.reports_dir / "leakage_ablation.json"
        if leak_path.is_file():
            for protocol, values in _json(leak_path).items():
                for metric, value in values.items():
                    _put_metric(N, f"{short}.l.{protocol}", metric, float(value))

    off_path = config.UNSW_NB15.reports_dir / "official_partitions.csv"
    if off_path.is_file():
        table = pd.read_csv(off_path)
        for (protocol, model), part in table.groupby(["protocol", "model"]):
            base = f"unsw.o.{protocol}.{model}"
            for metric in ("accuracy", "recall", "fpr", "roc_auc", "precision", "leaked_test_share"):
                N[f"{base}.{metric}"] = ff(float(part[metric].mean()), 4)
                N[f"{base}.{metric}_std"] = ff(float(part[metric].std()) if len(part) > 1 else 0.0, 4)
                if metric == "leaked_test_share":
                    N[f"{base}.leaked_pct"] = pct(float(part[metric].mean()))
            N[f"{base}.n_train"], N[f"{base}.n_test"] = fi(part["n_train"].mean()), fi(part["n_test"].mean())
    return N


# ---------------------------------------------------------------------------------- tables


def _md(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def _ds(short: str) -> config.DatasetSource:
    return config.get_dataset(DATASETS[short])


def tabla_modelos(short: str, point: str) -> str:
    metrics = pd.read_csv(_ds(short).reports_dir / "metrics.csv")
    test = metrics[(metrics["split"] == "test") & (metrics["operating_point"] == point)].set_index("model")
    rows = []
    for name in MODEL_ORDER:
        r = test.loc[name]
        rows.append(
            [pretty(name), ff(r.threshold), ff(r.recall), ff(r.fpr, 5), ff(r.precision), ff(r.f1), ff(r.accuracy),
             ff(r.roc_auc), fi(r.fn), fi(r.fp)]
        )
    return _md(["Modelo", "Umbral", "Recall", "FPR", "Precisión", "F1", "Accuracy", "ROC-AUC", "FN", "FP"], rows)


def tabla_semillas(short: str, point: str) -> str:
    summary = pd.read_csv(_ds(short).reports_dir / "multiseed_summary.csv")
    sub = summary[summary["operating_point"] == point].set_index("model")
    rows = []
    for name in MODEL_ORDER:
        r = sub.loc[name]
        rows.append(
            [pretty(name), f"{r.recall_mean:.4f} ± {r.recall_std:.4f}", f"{r.fpr_mean:.5f} ± {r.fpr_std:.5f}",
             f"{r.precision_mean:.4f} ± {r.precision_std:.4f}", f"{r.accuracy_mean:.4f} ± {r.accuracy_std:.4f}",
             f"{r.roc_auc_mean:.4f} ± {r.roc_auc_std:.4f}"]
        )
    return _md(["Modelo", "Recall", "FPR", "Precisión", "Accuracy", "ROC-AUC"], rows)


def tabla_diferencias_semillas(short: str) -> str:
    table = pd.read_csv(_ds(short).reports_dir / "multiseed_differences.csv")
    names = {"rf": "Random Forest", "xgb": "XGBoost", "mix": "Mix RF + XGB"}
    rows = []
    for algorithm in ("rf", "xgb", "mix"):
        for point in OPERATING_POINTS:
            sub = table[(table.algorithm == algorithm) & (table.operating_point == point)].set_index("metric")
            rows.append(
                [names[algorithm], POINT_TEXT[point],
                 f"{sub.loc['recall', 'mean_difference']:+.4f} ± {sub.loc['recall', 'std_difference']:.4f}",
                 f"{sub.loc['fpr', 'mean_difference']:+.5f} ± {sub.loc['fpr', 'std_difference']:.5f}",
                 f"{int(sub.loc['recall', 'seeds_better'])} de {int(sub.loc['recall', 'n_seeds'])}"]
            )
    return _md(["Algoritmo", "Punto de operación", "Diferencia de Recall", "Diferencia de FPR", "Semillas en que gana la mejorada"], rows)


def tabla_pareadas(short: str) -> str:
    table = pd.read_csv(_ds(short).reports_dir / "pairwise_tests.csv")
    rows = []
    for a, b in PAIRS:
        for point in ("recall_target", "fpr_budget"):
            sub = table[(table.model_a == a) & (table.model_b == b) & (table.operating_point == point)].set_index("metric")
            cells = []
            for metric, digits in (("recall", 4), ("fpr", 5)):
                r = sub.loc[metric]
                cells.append(
                    f"{r.difference:+.{digits}f} [{r.low:+.{digits}f}, {r.high:+.{digits}f}] (p={r.p_value:.3f})"
                )
            rows.append([f"{pretty(a)} menos {pretty(b)}", POINT_TEXT[point], *cells])
    return _md(["Comparación (A menos B)", "Punto de operación", "Diferencia de Recall", "Diferencia de FPR"], rows)


def _mean_std(values: pd.Series, digits: int = 4) -> str:
    if len(values) > 1:
        return f"{values.mean():.{digits}f} ± {values.std():.{digits}f}"
    return f"{values.iloc[0]:.{digits}f}"


def tabla_oficial() -> str:
    table = pd.read_csv(config.UNSW_NB15.reports_dir / "official_partitions.csv")
    rows = []
    for protocol, text in PROTOCOL_TEXT.items():
        for model in ("rf_baseline", "xgb_baseline"):
            part = table[(table.protocol == protocol) & (table.model == model)]

            def cell(metric: str, part: pd.DataFrame = part) -> str:
                return _mean_std(part[metric])

            rows.append(
                [text, pretty(model), fi(part.n_train.mean()), fi(part.n_test.mean()), pct(float(part.leaked_test_share.mean())),
                 cell("accuracy"), cell("recall"), cell("fpr"), cell("roc_auc")]
            )
    return _md(["Protocolo", "Modelo", "Entrenamiento", "Prueba", "Prueba repetida", "Accuracy", "Recall", "FPR", "ROC-AUC"], rows)


def tabla_ablacion(short: str) -> str:
    table = pd.read_csv(_ds(short).reports_dir / "feature_ablation.csv")
    rows = []
    for group in dict.fromkeys(table["group"]):
        sub = table[table["group"] == group].set_index("operating_point")
        dropped = sub["dropped"].iloc[0]
        rows.append(
            [group, dropped if isinstance(dropped, str) and dropped else "ninguna", ff(sub.loc["default", "recall"]),
             ff(sub.loc["default", "fpr"]), ff(sub.loc["recall_target", "fpr"]), ff(sub.loc["fpr_budget", "recall"]),
             ff(sub.loc["default", "roc_auc"])]
        )
    return _md(["Grupo quitado", "Variables", "Recall (0.5)", "FPR (0.5)", "FPR con Recall >= 0.95", "Recall con FPR <= 0.02", "ROC-AUC"], rows)


def tabla_fuga(short: str) -> str:
    data = _json(_ds(short).reports_dir / "leakage_ablation.json")
    names = {"naive": "Ingenuo (solo inf/NaN)", "dedup": "Sin duplicados", "full": "Completo (el del proyecto)"}
    rows = [
        [names[k], fi(v["rows"]), pct(v["leaked_test_share"]), ff(v["accuracy"]), ff(v["recall"]), ff(v["fpr"], 5)]
        for k, v in data.items()
    ]
    return _md(["Protocolo", "Filas", "Prueba con vector repetido", "Accuracy", "Recall", "FPR"], rows)


def tabla_familias(short: str) -> str:
    ds = _ds(short)
    summary = _json(ds.reports_dir / "training_summary.json")
    best = summary["best_model"]
    table = detection_by_attack_type(np.load(ds.models_dir / "scores.npz"), best, summary["thresholds"][best])
    rows = []
    for family, r in table.sort_values("recall_target", ascending=False).iterrows():
        label = f"{family} (falsas alarmas)" if family == config.BENIGN_LABEL else str(family)
        rows.append([label, fi(r["n"]), ff(r["default"]), ff(r["recall_target"]), ff(r["fpr_budget"])])
    return _md(["Tipo de tráfico", "Flujos de prueba", "Umbral 0.5", "Recall >= 0.95", "FPR <= 0.02"], rows)


def tabla_limpieza() -> str:
    rows = []
    for short in DATASETS:
        c = _json(_ds(short).cleaning_report_file)
        rows.append(
            [_ds(short).display_name, fi(c["rows_raw"]), fi(c["rows_removed_missing"]), fi(c["rows_removed_duplicates"]),
             fi(c["rows_removed_conflicting"]), fi(c["rows_final"]), str(c["n_features"])]
        )
    return _md(["Dataset", "Flujos crudos", "Con inf/NaN", "Duplicados", "Contradictorios", "Flujos limpios", "Variables"], rows)


def tabla_hiperparametros(short: str) -> str:
    summary = _json(_ds(short).reports_dir / "training_summary.json")
    rows = []
    for model in ("rf_improved", "xgb_improved"):
        info = summary["models"][model]
        params = ", ".join(f"{k.replace('clf__', '')}={v}" for k, v in sorted(info["best_params"].items()))
        rows.append([pretty(model), params, ff(info["cv_average_precision"]), fi(info["fit_seconds"])])
    return _md(["Modelo", "Hiperparámetros elegidos", "Precisión promedio en CV", "Segundos de ajuste final"], rows)


def tabla_importancias(short: str) -> str:
    summary = _json(_ds(short).reports_dir / "training_summary.json")
    items = list(summary["feature_importances"]["xgb_improved"].items())[:8]
    return _md(["Variable", "Importancia (XGBoost mejorado)"], [[f"`{k}`", ff(v, 3)] for k, v in items])


def tabla_umbrales(short: str) -> str:
    summary = _json(_ds(short).reports_dir / "training_summary.json")
    rows = [[pretty(m), *(ff(summary["thresholds"][m][p]) for p in OPERATING_POINTS)] for m in MODEL_ORDER]
    return _md(["Modelo", "Umbral 0.5", "Umbral con Recall >= 0.95", "Umbral con FPR <= 0.02"], rows)


def codigo(path: str, name: str) -> str:
    """Verbatim source of a function, class or method (`Class.method`) as a fenced code block."""
    source = (ROOT / path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    node: ast.AST | None = tree
    for part in name.split("."):
        node = next(
            (n for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == part), None
        )
        if node is None:
            raise KeyError(f"'{name}' not found in {path}")
    lines = source.splitlines()
    first = min([node.lineno, *[d.lineno for d in getattr(node, "decorator_list", [])]])
    block = textwrap.dedent("\n".join(lines[first - 1 : node.end_lineno]))
    return f"```python\n# {path}\n{block}\n```\n"


TABLES = {
    "codigo": codigo,
    "tabla_modelos": tabla_modelos,
    "tabla_semillas": tabla_semillas,
    "tabla_pareadas": tabla_pareadas,
    "tabla_diferencias_semillas": tabla_diferencias_semillas,
    "tabla_oficial": tabla_oficial,
    "tabla_ablacion": tabla_ablacion,
    "tabla_fuga": tabla_fuga,
    "tabla_familias": tabla_familias,
    "tabla_limpieza": tabla_limpieza,
    "tabla_hiperparametros": tabla_hiperparametros,
    "tabla_importancias": tabla_importancias,
    "tabla_umbrales": tabla_umbrales,
}
_TOKEN = re.compile(r"\{\{(>?)\s*([^}]+?)\s*\}\}")


def expand(text: str, numbers: dict[str, str], strict: bool = True, problems: list[str] | None = None) -> str:
    """Replace `{{key}}` and `{{>table args}}`; any unknown name is an error (or is listed if not strict)."""

    def fail(message: str, original: str) -> str:
        if strict:
            raise KeyError(message)
        if problems is not None:
            problems.append(message)
        return original

    def replace(match: re.Match[str]) -> str:
        is_table, body = match.group(1), match.group(2)
        if is_table:
            name, *args = body.split()
            if name not in TABLES:
                return fail(f"Unknown table '{name}'", match.group(0))
            try:
                return TABLES[name](*args).rstrip("\n")
            except (KeyError, TypeError, ValueError, FileNotFoundError) as error:
                return fail(f"Table '{body}' failed: {error!r}", match.group(0))
        if body not in numbers:
            return fail(f"Unknown number key '{body}'", match.group(0))
        return numbers[body]

    return _TOKEN.sub(replace, text)


if __name__ == "__main__":
    n = collect()
    print(len(n), "keys")
    for k in list(n)[:8]:
        print(k, "=", n[k])
