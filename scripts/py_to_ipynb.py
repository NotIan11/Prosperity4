"""Convert .py analysis scripts to .ipynb (flat: one code cell per file).

Usage:
    venv/bin/python scripts/py_to_ipynb.py FILE1.py [FILE2.py ...]
    venv/bin/python scripts/py_to_ipynb.py --all   # convert scripts/ + notebooks/

Output is written next to the source as FILE.ipynb.
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent.parent


def convert(py_path: Path) -> Path:
    src = py_path.read_text()
    nb = new_notebook()
    nb.cells.append(new_markdown_cell(f"# {py_path.name}\n\nAuto-generated from `{py_path.relative_to(ROOT)}`."))
    nb.cells.append(new_code_cell(src))
    out = py_path.with_suffix(".ipynb")
    nbformat.write(nb, out)
    return out


def main(argv: list[str]) -> None:
    if not argv or argv[0] == "--all":
        targets = sorted((ROOT / "scripts").glob("eda_*.py")) + sorted((ROOT / "notebooks").glob("*.py"))
    else:
        targets = [Path(a).resolve() for a in argv]
    for p in targets:
        out = convert(p)
        print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
