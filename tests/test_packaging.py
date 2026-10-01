"""TP-U8-7 (BR-U8-29..31): package metadata agrees with itself.

- ``requirements.txt`` lists exactly ``pyproject.toml``'s runtime dependencies.
- The license is MIT in both ``LICENSE`` and ``pyproject.toml``.
- The description is the purpose statement's English version.
- The four in-progress modules say so in their docstrings.
"""

from __future__ import annotations

import importlib
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
IN_PROGRESS = (
    "locus.world.wiki.cross_world",
    "locus.world.ingestion.concept_art_ingestor",
    "locus.world.augmentation.graph",
    "locus.world.wiki.distiller",
)


def _requirement_lines(text: str) -> list[str]:
    lines = (line.split("#", 1)[0].strip() for line in text.splitlines())
    return [re.sub(r"\s+", "", line) for line in lines if line]


def test_requirements_txt_matches_the_runtime_dependencies() -> None:
    listed = _requirement_lines((ROOT / "requirements.txt").read_text(encoding="utf-8"))
    declared = [re.sub(r"\s+", "", d) for d in PROJECT["dependencies"]]
    assert sorted(listed) == sorted(declared)
    assert len(listed) == len(set(listed))  # no duplicates


def test_the_license_is_mit_in_both_places() -> None:
    assert PROJECT["license"] == {"text": "MIT"}
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").splitlines()[0] == "MIT License"


def test_the_description_is_the_purpose_statement() -> None:
    text = PROJECT["description"]
    for part in ("solo TRPG", "rumors and events spread along the terrain", "each region"):
        assert part in text
    assert PROJECT["urls"]["Repository"] == "https://github.com/hongsam14/Locus"


def test_in_progress_modules_say_so() -> None:
    for name in IN_PROGRESS:
        doc = importlib.import_module(name).__doc__ or ""
        assert doc.startswith("STATUS: in-progress — "), name
