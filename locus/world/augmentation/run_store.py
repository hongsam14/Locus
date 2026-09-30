"""Augmentation run storage (U7, FD7-Q5=A).

An augmentation *run* is one detect -> ask -> apply loop over a world (the word
"session" is reserved for game sessions in the play boundary, FR-A5).
In-memory for MVP; the ``RunStore`` protocol allows swapping in a PostgreSQL
implementation later without touching the service.
"""

from __future__ import annotations

from typing import Protocol

from locus.world.augmentation.types import AugmentationRun


class RunStore(Protocol):
    def save(self, run: AugmentationRun) -> None: ...
    def get(self, run_id: str) -> AugmentationRun | None: ...


class InMemoryRunStore(RunStore):
    def __init__(self) -> None:
        self._runs: dict[str, AugmentationRun] = {}

    def save(self, run: AugmentationRun) -> None:
        self._runs[run.id] = run

    def get(self, run_id: str) -> AugmentationRun | None:
        return self._runs.get(run_id)
