"""RumorService — session rumor generation and support (S2, FR-R2/R5).

Owns everything about a region's session rumors: generating a distortion chain
from canonical sources + existing rumors, wiping-and-regenerating, and adjusting
a rumor's support. Canonical access (ConsensusEngine) is read-only (NFR-R2).
"""

from __future__ import annotations

from ..consensus.engine import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from ..query.loader import WorldLoader
from .base import SessionAppService, clamp
from .models import DEFAULT_DISTORTION_DEGREE, GameSession, SessionRumor, TimelineKind
from .repository import SessionRepository
from .rumor_generator import RumorGenerator

# Q1=A: chain degrees = region_distortion * these fractions (region degree = cap).
DEFAULT_CHAIN_FRACTIONS = [1 / 3, 2 / 3, 1.0]


class RumorService(SessionAppService):
    """Generate / regenerate rumors and adjust their support."""

    def __init__(
        self,
        repo: SessionRepository,
        generator: RumorGenerator,
        loader: WorldLoader,
        params: ConsensusParams = DEFAULT_PARAMS,
    ) -> None:
        super().__init__(repo)
        self._gen = generator
        self._loader = loader
        self._params = params

    # -- reads ---------------------------------------------------------------
    def list_rumors(self, session_id: str, region_id: str) -> list[SessionRumor]:
        """Read-only list of a region's session rumors (allowed on closed sessions)."""
        self._require_session(session_id)
        return self._repo.list_rumors(session_id, region_id)

    # -- actions -------------------------------------------------------------
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
        rumor.support = clamp(support)
        saved = self._repo.upsert_rumor(rumor)
        self._timeline(
            session,
            TimelineKind.ADJUST_SUPPORT,
            f"support of {rumor_id} -> {rumor.support:.2f}",
            {"rumor_id": rumor_id, "support": rumor.support},
        )
        return saved

    def append_for_region(self, session: GameSession, region_id: str) -> list[SessionRumor]:
        """Append rumors at the region's current distortion, preserving existing
        rumors + support (used by TurnAdvancer; FR-P4.1 / BR-P2-7). Not timelined —
        the turn summary covers it."""
        return self._generate_for_region(
            session, region_id, self._chain_degrees(session.id, region_id)
        )

    # -- internals -----------------------------------------------------------
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
        return [clamp(f * d) for f in DEFAULT_CHAIN_FRACTIONS]
