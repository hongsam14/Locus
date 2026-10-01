"""US-7.2 — the boundary dependency matrix is enforced by import inspection.

Allowed (component-dependency.md §1):
  shared -> (nothing internal)
  knowledge -> shared
  world -> knowledge, shared
  play -> knowledge, shared
  localization -> shared
``locus/**`` never imports ``api``; ``api`` (the composition root) may import
everything and is not checked as an importer. ``locus/__main__.py`` is the CLI
composition root and may import every boundary.
"""

from __future__ import annotations

import ast
from pathlib import Path

LOCUS = Path(__file__).resolve().parents[1] / "locus"

ALLOWED = {
    "shared": {"shared"},
    "knowledge": {"shared", "knowledge"},
    "world": {"shared", "knowledge", "world"},
    "play": {"shared", "knowledge", "play"},
    "localization": {"shared", "localization"},
}
COMPOSITION_ROOTS = {"__main__", "__init__"}  # locus/__main__.py, locus/__init__.py


def _boundary_of(path: Path) -> str:
    rel = path.relative_to(LOCUS)
    return rel.parts[0].removesuffix(".py")


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module == "locus":  # `from locus import play` imports the subpackage
                names.extend(f"locus.{alias.name}" for alias in node.names)
            else:
                names.append(node.module)
    return names


def _violations() -> list[str]:
    out: list[str] = []
    for path in sorted(LOCUS.rglob("*.py")):
        boundary = _boundary_of(path)
        for name in _imports(path):
            if name == "api" or name.startswith("api."):
                out.append(f"{path.relative_to(LOCUS.parent)}: imports {name} (locus -> api)")
                continue
            if not name.startswith("locus."):
                continue
            target = name.split(".")[1]
            if target not in ALLOWED:  # e.g. locus.__main__
                continue
            if boundary in COMPOSITION_ROOTS:
                continue
            if boundary not in ALLOWED:
                out.append(f"{path.relative_to(LOCUS.parent)}: unknown boundary {boundary!r}")
                continue
            if target not in ALLOWED[boundary]:
                out.append(f"{path.relative_to(LOCUS.parent)}: {boundary} -> {target} via {name}")
    return out


def test_no_relative_imports_left() -> None:
    for path in LOCUS.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level > 0]
        assert not rel, f"{path}: relative imports are not allowed inside locus/"


def test_boundary_matrix_is_respected() -> None:
    violations = _violations()
    assert not violations, "\n".join(violations)


def test_every_top_level_package_is_a_known_boundary() -> None:
    packages = {p.name for p in LOCUS.iterdir() if p.is_dir() and not p.name.startswith("__")}
    assert packages == set(ALLOWED), packages


def test_only_composition_roots_live_at_the_top_level() -> None:
    modules = {p.stem for p in LOCUS.glob("*.py")}
    assert modules <= COMPOSITION_ROOTS, modules - COMPOSITION_ROOTS
