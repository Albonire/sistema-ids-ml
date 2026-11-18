"""Build the four PDFs of the delivery package from the markdown sources.

Usage (from the repository root):
    python docs/entrega/build.py [informe guia guion diapositivas] [--fecha "19 de noviembre de 2026"]

Needs: pandoc, Node with Playwright and its Chromium, and the Python package pypdf.
Steps per document: expand `{{numbers}}` and `{{>tables}}` from the reports, convert to HTML with
pandoc (smart typography off, so `--` never becomes an en dash), render to PDF with Chromium, then
re-render once more with page numbers written into the table of contents.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pypdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import datos_docs  # noqa: E402

SOURCES, BUILD, OUT = HERE / "fuentes", HERE / "_build", HERE / "pdf"
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre"]
FORMAT = "markdown-smart+fenced_divs+tex_math_dollars+pipe_tables+implicit_figures+backtick_code_blocks+fenced_code_attributes+link_attributes+raw_html"

DOCS = {
    "informe": {
        "source": "informe_final.md", "output": "Informe_Final_IDS", "toc": True, "numbered": True,
        "tipo": "Informe final",
        "titulo": "Sistema inteligente de detección de intrusiones de red con aprendizaje automático",
        "subtitulo": "Comparación de Random Forest, XGBoost y su combinación en UNSW-NB15 y CICIDS2017, con evaluación libre de fuga de datos",
        "footer": "Informe final · IDS con aprendizaje automático",
    },
    "guia": {
        "source": ["guia_a_teoria.md", "guia_b_codigo.md", "guia_c_ejemplos.md", "guia_d_repaso.md"], "output": "Guia_de_Estudio_IDS", "toc": True, "numbered": False,
        "tipo": "Guía de estudio",
        "titulo": "Todo lo que hay que saber del proyecto IDS",
        "subtitulo": "Teoría, código importante, ejemplos resueltos a mano y preguntas de repaso",
        "footer": "Guía de estudio · IDS con aprendizaje automático",
    },
    "guion": {
        "source": "guion_sustentacion.md", "output": "Guion_Sustentacion_IDS", "toc": False, "numbered": False,
        "tipo": "Guion de la sustentación",
        "titulo": "Guion completo de 10 minutos",
        "subtitulo": "Texto para decir, tiempos, relevos entre expositores, demostración y plan B",
        "footer": "Guion de sustentación · IDS con aprendizaje automático",
    },
    "diapositivas": {
        "source": "contenido_diapositivas.md", "output": "Contenido_Diapositivas_IDS", "toc": False, "numbered": False,
        "tipo": "Contenido de las diapositivas",
        "titulo": "Qué lleva cada diapositiva",
        "subtitulo": "Texto exacto, imágenes, diagramas y gráficas sugeridas, y diseño",
        "footer": "Contenido de diapositivas · IDS con aprendizaje automático",
    },
}


def run(command: list[str], **kwargs) -> None:
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:3])} failed:\n{result.stderr or result.stdout}")
    if result.stderr.strip():
        print(result.stderr.strip())


def to_html(markdown: Path, html: Path, spec: dict, fecha: str) -> None:
    command = [
        "pandoc", str(markdown), "-f", FORMAT, "-t", "html5", "-s", "--template", str(HERE / "plantilla.html"),
        "--mathml", "--highlight-style=tango", "--embed-resources", f"--resource-path={HERE}",
        "-c", "estilo.css", "-o", str(html),
        "-M", f"pagetitle={spec['tipo']}: {spec['titulo']}", "-M", f"tipo={spec['tipo']}",
        "-M", f"titulo={spec['titulo']}", "-M", f"subtitulo={spec['subtitulo']}", "-M", f"fecha={fecha}",
        "-M", "author-meta=Silvana, Fabian, Raul", "-M", "lang=es",
    ]
    if spec["toc"]:
        command += ["--toc", "--toc-depth=3"]
    if spec["numbered"]:
        command += ["--number-sections"]
    run(command)


def render(html: Path, pdf: Path, footer: str) -> None:
    run(["node", str(HERE / "render.js"), str(html), str(pdf), footer], cwd=HERE)


def outline_pages(pdf: Path, max_depth: int = 3) -> list[int]:
    """Page number of every heading down to `max_depth`, in document order."""
    reader = pypdf.PdfReader(str(pdf))
    pages: list[int] = []

    def walk(items: list, depth: int) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
            elif depth <= max_depth:
                pages.append(reader.get_destination_page_number(item) + 1)

    walk(reader.outline, 1)
    return pages


def add_toc_pages(html: Path, pages: list[int]) -> bool:
    """Write the page number in front of every table-of-contents entry; False if counts differ."""
    text = html.read_text(encoding="utf-8")
    start = text.find('<nav id="TOC"')
    end = text.find("</nav>", start)
    if start < 0 or end < 0:
        return False
    nav = text[start:end]
    anchors = list(re.finditer(r"<a href=\"#", nav))
    if len(anchors) != len(pages):
        print(f"  TOC entries {len(anchors)} differ from outline {len(pages)}; page numbers skipped")
        return False
    out, last = [], 0
    for match, page in zip(anchors, pages, strict=True):
        out.append(nav[last:match.start()])
        out.append(f'<span class="pg">{page}</span>')
        last = match.start()
    out.append(nav[last:])
    html.write_text(text[:start] + "".join(out) + text[end:], encoding="utf-8")
    return True


def build(name: str, fecha: str, numbers: dict[str, str]) -> Path:
    spec = DOCS[name]
    BUILD.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    names = spec["source"] if isinstance(spec["source"], list) else [spec["source"]]
    source = "\n\n".join((SOURCES / n).read_text(encoding="utf-8") for n in names if (SOURCES / n).is_file())
    expanded = datos_docs.expand(source, numbers)
    markdown = BUILD / f"{name}.md"
    markdown.write_text(expanded, encoding="utf-8")
    html, pdf = BUILD / f"{name}.html", BUILD / f"{spec['output']}.pdf"
    to_html(markdown, html, spec, fecha)
    render(html, pdf, spec["footer"])
    if spec["toc"] and add_toc_pages(html, outline_pages(pdf)):
        render(html, pdf, spec["footer"])
    target = OUT / pdf.name
    shutil.copy(pdf, target)
    reader = pypdf.PdfReader(str(target))
    print(f"{name}: {target.name}, {len(reader.pages)} pages, {target.stat().st_size / 1e6:.1f} MB")
    return target


def main(argv: list[str] | None = None) -> int:
    today = dt.date.today()
    parser = argparse.ArgumentParser(description="Build the delivery PDFs.")
    parser.add_argument("documents", nargs="*", default=list(DOCS))
    parser.add_argument("--fecha", default=f"{today.day} de {MONTHS[today.month - 1]} de {today.year}")
    args = parser.parse_args(argv)
    numbers = datos_docs.collect()
    for name in args.documents:
        if name not in DOCS:
            parser.error(f"unknown document '{name}'")
        build(name, args.fecha, numbers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
