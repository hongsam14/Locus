"""GameMasterService — per-turn session orchestrator (S2, FR-R2/R3/R4).

Drives one session's dynamic state a turn at a time: generate / regenerate
rumors, adjust support, set per-region distortion, and advance the turn
(re-evaluating promotion). Every action records exactly one TimelineEntry.
Canonical access (source collection via ConsensusEngine) is read-only (NFR-R2).
"""

from __future__ import annotations

from ..consensus.engine import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from ..models import LocusModel
from ..query.loader import WorldLoader
from . import promotion
from .models import (
    DEFAULT_DISTORTION_DEGREE,
    GameSession,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from .repository import SessionRepository
from .rumor_generator import RumorGenerator

# Q1=A: chain degrees = region_distortion * these fractions (region degree = cap).
DEFAULT_CHAIN_FRACTIONS = [1 / 3, 2 / 3, 1.0]


class SessionClosedError(RuntimeError):
    """Raised when a write action targets a CLOSED session (BR-S2-9)."""


class TurnResult(LocusModel):
    """Summary of an advance_turn call."""

    session_id: str
    turn: int
    promoted_ids: list[str] = []
    demoted_ids: list[str] = []


class GameMasterService:
    def __init__(
        self,
        repo: SessionRepository,
        generator: RumorGenerator,
        loader: WorldLoader,
        params: ConsensusParams = DEFAULT_PARAMS,
    ) -> None:
        self._repo = repo
        self._gen = generator
        self._loader = loader
        self._params = params

    # -- reads ------------------------------------------------------------ #
    def list_rumors(self, session_id: str, region_id: str) -> list[SessionRumor]:
        """Read-only list of a region's session rumors (allowed on closed sessions)."""
        if self._repo.get_session(session_id) is None:
            raise LookupError(f"session not found: {session_id}")
        return self._repo.list_rumors(session_id, region_id)

    # -- actions ---------------------------------------------------------- #
    def generate_rumors(
        self, session_id: str, region_id: str, *, degrees: list[float] | None = None
    ) -> list[SessionRumor]:
        session = self._require_open(session_id)
        degrees = degrees or self._chain_degrees(session_id, region_id)
        rumors = self._generate_for_region(session, region_id, degrees)
        self._timeline(
            session,
            TimelineKind.GENERATE,
            f"generated {len(rumors)} rumors in {region_id}",
            {"region_id": region_id, "rumor_ids": [r.id for r in rumors]},
        )
        return rumors

    def regenerate_region(self, session_id: str, region_id: str) -> list[SessionRumor]:
        session = self._require_open(session_id)
        existing = self._repo.list_rumors(session_id, region_id)
        for r in existing:  # Q4=A: drop all (incl. promoted) then regenerate
            self._repo.delete_rumor(session_id, r.id)
        degrees = self._chain_degrees(session_id, region_id)
        rumors = self._generate_for_region(session, region_id, degrees)
        self._timeline(
            session,
            TimelineKind.REGENERATE,
            f"regenerated {region_id}",
            {
                "region_id": region_id,
                "deleted": [r.id for r in existing],
                "rumor_ids": [r.id for r in rumors],
            },
        )
        return rumors

    def adjust_support(self, session_id: str, rumor_id: str, support: float) -> SessionRumor:
        session = self._require_open(session_id)
        rumor = self._repo.get_rumor(session_id, rumor_id)
        if rumor is None:
            raise LookupError(f"rumor not found: {rumor_id}")
        rumor.support = _clamp(support)
        saved = self._repo.upsert_rumor(rumor)
        self._timeline(
            session,
            TimelineKind.ADJUST_SUPPORT,
            f"support of {rumor_id} -> {rumor.support:.2f}",
            {"rumor_id": rumor_id, "support": rumor.support},
        )
        return saved

    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        session = self._require_open(session_id)
        degree = _clamp(degree)
        self._repo.set_region_distortion(session_id, region_id, degree)
        self._timeline(
            session,
            TimelineKind.SET_DISTORTION,
            f"distortion of {region_id} -> {degree:.2f}",
            {"region_id": region_id, "degree": degree},
        )

    def advance_turn(
        self, session_id: str, *, promotion_threshold: float = promotion.DEFAULT_PROMOTION_THRESHOLD
    ) -> TurnResult:
        session = self._require_open(session_id)
        rumors = self._repo.list_rumors(session_id)
        res = promotion.evaluate(rumors, promotion_threshold)
        for rid in res.promoted_ids:
            self._set_promoted(session_id, rid, True)
            self._timeline(session, TimelineKind.PROMOTE, f"promoted {rid}", {"rumor_id": rid})
        for rid in res.demoted_ids:
            self._set_promoted(session_id, rid, False)
            self._timeline(session, TimelineKind.DEMOTE, f"demoted {rid}", {"rumor_id": rid})
        new_turn = self._repo.bump_turn(session_id)
        self._timeline(
            session,
            TimelineKind.ADVANCE_TURN,
            f"advanced to turn {new_turn}",
            {"promoted": res.promoted_ids, "demoted": res.demoted_ids},
            turn=new_turn,
        )
        return TurnResult(
            session_id=session_id,
            turn=new_turn,
            promoted_ids=res.promoted_ids,
            demoted_ids=res.demoted_ids,
        )

    # -- internals -------------------------------------------------------- #
    def _generate_for_region(
        self, session: GameSession, region_id: str, degrees: list[float]
    ) -> list[SessionRumor]:
        rumors: list[SessionRumor] = []
        for text, sid, kind, conf in self._collect_sources(session.world_id, region_id, session.id):
            chain = self._gen.generate_chain(
                source_text=text,
                source_id=sid,
                source_kind=kind,
                source_confidence=conf,
                region_id=region_id,
                session_id=session.id,
                degrees=degrees,
            )
            for r in chain:
                rumors.append(self._repo.upsert_rumor(r))
        return rumors

    def _collect_sources(
        self, world_id: str, region_id: str, session_id: str
    ) -> list[tuple[str, str, str, float]]:
        """Sources = region direct + propagated canonical knowledge + existing
        session rumors (Q2). (text, id, kind, confidence)."""
        kg, topo = self._loader.load(world_id)
        if region_id not in {r.id for r in topo.regions}:
            raise LookupError(f"region not found: {region_id}")
        view = ConsensusEngine(kg, topo, self._params).resolve(region_id)
        sources: list[tuple[str, str, str, float]] = []
        for kv in view.direct + view.propagated:  # Q2: direct + propagated
            sources.append((kv.statement, kv.knowledge_id, "knowledge", kv.confidence))
        for r in self._repo.list_rumors(session_id, region_id):  # existing rumors (chain)
            sources.append((r.statement, r.id, "rumor", r.confidence))
        return sources

    def _chain_degrees(self, session_id: str, region_id: str) -> list[float]:
        d = self._repo.get_region_distortion(session_id, region_id)
        if d is None:
            d = DEFAULT_DISTORTION_DEGREE
        return [_clamp(f * d) for f in DEFAULT_CHAIN_FRACTIONS]

    def _set_promoted(self, session_id: str, rumor_id: str, promoted: bool) -> None:
        rumor = self._repo.get_rumor(session_id, rumor_id)
        if rumor is None:  # pragma: no cover - id came from list_rumors
            return
        rumor.promoted = promoted
        self._repo.upsert_rumor(rumor)

    def _timeline(
        self,
        session: GameSession,
        kind: TimelineKind,
        summary: str,
        payload: dict,
        *,
        turn: int | None = None,
    ) -> None:
        self._repo.append_timeline(
            TimelineEntry(
                session_id=session.id,
                turn=session.turn if turn is None else turn,
                kind=kind,
                summary=summary,
                payload=payload,
            )
        )

    def _require_open(self, session_id: str) -> GameSession:
        session = self._repo.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        if session.status == SessionStatus.CLOSED.value:
            raise SessionClosedError(f"session is closed: {session_id}")
        return session


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
