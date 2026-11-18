"""Check one markdown source: unknown `{{keys}}` or tables, and forbidden characters.

Usage (from the repository root):
    python docs/entrega/check_source.py docs/entrega/fuentes/guia_a_teoria.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import datos_docs  # noqa: E402

FORBIDDEN = re.compile("[–—\U0001F300-\U0001FAFF☀-➿]")


def main(paths: list[str]) -> int:
    numbers = datos_docs.collect()
    bad = 0
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        problems: list[str] = []
        expanded = datos_docs.expand(text, numbers, strict=False, problems=problems)
        for problem in problems:
            print(f"{path}: {problem}")
        for number, line in enumerate(expanded.splitlines(), 1):
            if FORBIDDEN.search(line):
                print(f"{path}:{number}: forbidden character (en dash, em dash or emoji)")
                bad += 1
            if " -- " in line:
                print(f"{path}:{number}: double hyphen (renders literally; use a colon or a comma)")
                bad += 1
        bad += len(problems)
        words = len(re.findall(r"\w+", expanded))
        print(f"{path}: {words} words, {len(problems)} unresolved placeholders")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
