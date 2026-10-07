"""Augmentation run storage (U7 FD7-Q5=A; U3 BR-U3-42, NFR N3-7).

A *run* is one detect -> ask -> apply loop over a world ("session" is the play
boundary's word, FR-A5). Runs live in process memory only: a restart loses them (the
screen then offers a new search), and each world keeps its latest 20. Each run has a
lock so two requests on one run take turns — the latest-first undo and "undo once"
hold under concurrent clicks — and the run's own caches: polished question text by
issue key, wiki-conflict verdicts and wiki lookups (BR-U3-41).
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Protocol

from locus.world.augmentation.types import AugmentationRun

RUNS_PER_WORLD = 20


@dataclass
class RunState:
    run: AugmentationRun
    lock: threading.Lock = field(default_factory=threading.Lock)
    polished: dict[str, str] = field(default_factory=dict)
    verdicts: dict[tuple[str, str, str], tuple[bool, str]] = field(default_factory=dict)
    lookups: dict[tuple[str, str], list] = field(default_factory=dict)


class RunStore(Protocol):
    def save(self, state: RunState) -> None: ...
    def get(self, run_id: str) -> RunState | None: ...


class InMemoryRunStore:
    def __init__(self, *, per_world: int = RUNS_PER_WORLD) -> None:
        self._runs: OrderedDict[str, RunState] = OrderedDict()
        self._per_world = per_world
        self._lock = threading.Lock()

    def save(self, state: RunState) -> None:
        with self._lock:
            self._runs[state.run.id] = state
            self._runs.move_to_end(state.run.id)
            same = [rid for rid, s in self._runs.items() if s.run.world_id == state.run.world_id]
            for rid in same[: max(0, len(same) - self._per_world)]:
                del self._runs[rid]

    def get(self, run_id: str) -> RunState | None:
        with self._lock:
            return self._runs.get(run_id)
