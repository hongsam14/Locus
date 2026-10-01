"""TP-U8-6 (BR-U8-1): code never names a demo — demos are data.

Scans the shipped code for the packaged demo's and the old demo's names and region
names. Excluded: the demo package data itself, the test fixtures, and the web tests.
``web/src`` joins the scan in U8 Step 10, once the home screen reads the manifest.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNED = ("locus", "api")
SKIP = ("locus/world/demo/worlds/",)
NAMES = re.compile(
    r"emberleaf|aldermoor|riverton|highcrag|greenvale|frostreach|saltwake|sylvarch|"
    r"ambermeadow|ironcrag|gutterlight|hollowdeep|sunstrand|ashen.dig|greenreach|stonebrow|"
    r"saltmarch",
    re.IGNORECASE,
)


def test_tp_u8_6_no_demo_name_in_code() -> None:
    hits = []
    for top in SCANNED:
        for path in sorted((ROOT / top).rglob("*")):
            rel = path.relative_to(ROOT).as_posix()
            if not path.is_file() or path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            if any(rel.startswith(s) for s in SKIP):
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if NAMES.search(line):
                    hits.append(f"{rel}:{n}: {line.strip()}")
    assert hits == []
