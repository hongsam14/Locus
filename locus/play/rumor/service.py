"""RumorService — session rumor generation and support (S2, FR-R2/R5).

Owns everything about a region's session rumors: generating a distortion chain
from canonical sources + existing rumors, wiping-and-regenerating, and adjusting
a rumor's support. Canonical access (ConsensusEngine) is read-only (NFR-R2).
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.knowledge.consensus import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from locus.play.base import SessionAppService
from locus.play.errors import LlmUnavailableError
from locus.play.models import (
    DEFAULT_DISTORTION_DEGREE,
    Deed,
    DeedAppraisal,
    GameSession,
    RegenerateResult,
    SessionRumor,
    SpreadTarget,
    TimelineKind,
)
from locus.play.ports import PlayRepository
from locus.play.rumor import dynamics as rumor_dynamics
from locus.play.rumor.generator import RumorGenerator
from locus.play.turn.budget import LlmBudget
from locus.shared.models import Provenance, SourceKind
from locus.shared.models.util import clamp01

# Q1=A: chain degrees = region_distortion * these fractions (region degree = cap).
DEFAULT_CHAIN_FRACTIONS = [1 / 3, 2 / 3, 1.0]

# append_for_turn's second value: why a region got fewer drafts than it could have
SKIP_CAPPED = "capped"  # active-rumor cap reached (BR-U4-18 / FD R-15)
SKIP_BUDGET = "budget"  # LLM budget for this turn exhausted (BR-U4-17)
SKIP_LLM_FAILED = "llm_failed"  # a chain came back short: circuit breaker (NFR R-02)


def chain_degrees_for(distortion: float | None) -> list[float]:
    """Chain degrees for a region distortion (pure; Q1=A). ``None`` = default."""
    d = DEFAULT_DISTORTION_DEGREE if distortion is None else distortion
    return [clamp01(f * d) for f in DEFAULT_CHAIN_FRACTIONS]


class RumorService(SessionAppService):
    """Generate / regenerate rumors and adjust their support."""

    def __init__(
        self,
        repo: PlayRepository,
        generator: RumorGenerator | None,
        snapshots: SnapshotSource,
        params: ConsensusParams = DEFAULT_PARAMS,
        *,
        birth_support: float = 0.0,
    ) -> None:
        super().__init__(repo)
        self._gen = generator  # None without an LLM provider: reads still work (#13)
        self._snapshots = snapshots
        self._params = params
        self._birth_support = birth_support  # seed support for new rumors (BR-H1-21)

    @property
    def llm_available(self) -> bool:
        return self._gen is not None

    def _require_generator(self) -> RumorGenerator:
        if self._gen is None:
            raise LlmUnavailableError("rumor generation needs an LLM provider (set OPENAI_API_KEY)")
        return self._gen

    # -- reads ---------------------------------------------------------------
    def list_rumors(self, session_id: str, region_id: str) -> list[SessionRumor]:
        """Read-only list of a region's session rumors (allowed on closed sessions)."""
        self._require_session(session_id)
        return self._repo.list_rumors(session_id, region_id)

    # -- actions -------------------------------------------------------------

    def _region_name(self, session: GameSession, region_id: str) -> str:
        """The region's name for timeline lines (FR-D3); its id when the world lost it."""
        region = self._snapshots.get(session.world_id).regions_by_id.get(region_id)
        return region.name if region is not None else region_id

    def generate_rumors(
        self, session_id: str, region_id: str, *, degrees: list[float] | None = None
    ) -> list[SessionRumor]:
        self._require_generator()
        session = self._require_open(session_id)
        degrees = degrees or self._chain_degrees(session_id, region_id)
        rumors = self._generate_for_region(session, region_id, degrees)
        self._timeline(
            session,
            TimelineKind.GENERATE,
            f"generated {len(rumors)} rumors in {self._region_name(session, region_id)}",
            {
                "region_id": region_id,
                "region_name": self._region_name(session, region_id),
                "rumor_ids": [r.id for r in rumors],
            },
        )
        return rumors

    def regenerate_region(self, session_id: str, region_id: str) -> RegenerateResult:
        """Replace the region's non-promoted canonical rumors (U5: returns what was
        replaced so the API can purge their translations — the skip paths touch nothing).
        U7: the replaced rumors are deactivated, never deleted (BR-U7-16)."""
        self._require_generator()
        session = self._require_open(session_id)
        existing = self._repo.list_rumors(session_id, region_id)
        name = self._region_name(session, region_id)  # FR-D3
        # FR-UX2.5 / BR-X3-9 (X3): preserve promoted rumors; drop only the
        # non-promoted ones then regenerate. (Was Q4=A drop-all incl. promoted.)
        # U6 (BR-U6-29): a player's deed rumors are only undone by a GM void, never by a
        # regenerate — keep them with the promoted ones and drop canonical rumors only.
        kept = [r for r in existing if r.promoted or r.origin_kind != "canonical"]
        dropped = [r for r in existing if not r.promoted and r.origin_kind == "canonical"]
        degrees = self._chain_degrees(session_id, region_id)
        # Draft BEFORE deleting anything. The generator swallows LLM failures and
        # returns an empty chain, so deleting first destroyed the region's rumors
        # (support, promotion history, provenance) and still answered 200 during an
        # LLM outage (code review U4 #3). Reseed from canonical knowledge only —
        # kept promoted rumors must not become chain seeds (X3 review #1 / BR-X3-9).
        fresh, complete = self._draft_for_region(
            session, region_id, degrees, include_existing=False
        )
        if not complete:
            # Part of the chain failed: replacing now would delete rumors we cannot
            # replace. `fresh == []` alone was not enough — it also means "no canonical
            # source to seed", which legitimately clears the region (U4-2 #6).
            self._timeline(
                session,
                TimelineKind.REGENERATE,
                f"regenerated {name}: generation incomplete, kept everything",
                {
                    "region_id": region_id,
                    "region_name": name,
                    "deactivated": [],
                    "kept": [r.id for r in existing],
                    "rumor_ids": [],
                    "skipped": True,
                    "reason": "llm_incomplete",
                },
            )
            return RegenerateResult(kept=existing, skipped_reason="llm_incomplete")
        if not fresh and not dropped:
            self._timeline(
                session,
                TimelineKind.REGENERATE,
                f"regenerated {name}: nothing to seed",
                {
                    "region_id": region_id,
                    "region_name": name,
                    "deactivated": [],
                    "kept": [r.id for r in existing],
                    "rumor_ids": [],
                    "skipped": True,
                    "reason": "no_sources",
                },
            )
            return RegenerateResult(kept=existing, skipped_reason="no_sources")
        with self._repo.uow() as u:  # swap in one transaction (BR-U4-14)
            # Deactivated, never deleted: a kept rumor's `distorted_from_id` keeps pointing
            # at a row, so its chain can still be walked to the root (BR-U7-16, RE C6).
            for r in dropped:
                r.active = False
            if dropped:
                u.rumors.upsert_rumors(dropped)
            saved = u.rumors.upsert_rumors(fresh) if fresh else []
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.REGENERATE,
                    f"regenerated {name}",
                    {
                        "region_id": region_id,
                        "region_name": name,
                        "deactivated": [r.id for r in dropped],
                        "kept": [r.id for r in kept],
                        "rumor_ids": [r.id for r in saved],
                    },
                )
            )
        return RegenerateResult(kept=kept, fresh=saved, deactivated_ids=[r.id for r in dropped])

    def adjust_support(self, session_id: str, rumor_id: str, support: float) -> SessionRumor:
        session = self._require_open(session_id)
        rumor = self._repo.get_rumor(session_id, rumor_id)
        if rumor is None:
            raise LookupError(f"rumor not found: {rumor_id}")
        rumor.support = clamp01(support)
        saved = self._repo.upsert_rumor(rumor)
        self._timeline(
            session,
            TimelineKind.ADJUST_SUPPORT,
            f"support of a rumor in {self._region_name(session, rumor.region_id)}"
            f" -> {rumor.support:.2f}",
            {
                "rumor_id": rumor_id,
                "support": rumor.support,
                "region_id": rumor.region_id,
                "region_name": self._region_name(session, rumor.region_id),
            },
        )
        return saved

    def append_for_turn(
        self,
        session: GameSession,
        region_id: str,
        *,
        distortion: float | None,
        budget: LlmBudget,
        max_new: int,
        max_active: int,
        min_source_support: float | None = None,
        reserved: int = 0,
    ) -> tuple[list[SessionRumor], str | None]:
        """Draft this turn's new rumors for one region **without saving** (U4;
        BLM §4.4, BR-U4-17/18/19). The caller persists the drafts inside the turn's
        unit of work.

        ``distortion`` is the post-event distortion the turn computed (BR-U4-14).
        Chain length per source = ``min(len(degrees), budget.remaining,
        max_new - drafted, max_active - active)`` so no reserved call is wasted
        (FD R-05) and a turn never pushes a region above the active cap
        (FD R-15 / NFR R-01). Canonical knowledge that already has an active
        derived rumor here is not re-seeded (BR-U4-19). Returns the drafts and a
        skip reason (``SKIP_*``) or ``None``. A chain shorter than requested means
        the LLM failed: the region's remaining drafts are abandoned (``llm_failed``)
        and the caller trips its circuit breaker (NFR R-02)."""
        active = self._repo.list_rumors(session.id, region_id)
        # ``reserved``: deed seeds and spread hops this turn already put here, not saved
        # yet — the active cap counts them too (U6 BR-U6-15, TP-U6-8).
        room = max_active - len(active) - reserved
        if room <= 0:
            return [], SKIP_CAPPED
        seeded = {r.distorted_from_id for r in active if r.distorted_from_kind == "knowledge"}
        sources = self._collect_sources(
            session.world_id,
            region_id,
            session.id,
            min_source_support=min_source_support,
            exclude_knowledge_ids=seeded,
        )
        degrees = chain_degrees_for(distortion)
        out: list[SessionRumor] = []
        reason: str | None = None
        for text, sid, kind, conf in sources:
            n = min(len(degrees), budget.remaining, max_new - len(out), room - len(out))
            if n <= 0:
                if budget.exhausted and len(out) < min(max_new, room):
                    reason = SKIP_BUDGET
                break
            chain = self._require_generator().generate_chain(
                source_text=text,
                source_id=sid,
                source_kind=kind,
                source_confidence=conf,
                region_id=region_id,
                session_id=session.id,
                degrees=degrees[:n],
                birth_support=self._birth_support,
            )
            budget.take(n)  # reserved calls = degree steps (upper bound, FD R-13)
            out.extend(chain)
            if len(chain) < n:
                reason = SKIP_LLM_FAILED
                break
        return out, reason

    # -- U6 deed rumors -------------------------------------------------------
    def seed(
        self, session: GameSession, deed: Deed, appraisal: DeedAppraisal, *, distortion: float
    ) -> SessionRumor:
        """A deed rumor born from an NPC's retelling — no LLM call (BR-U6-14, FD
        deviation 2): the NPC's words already are this region's distortion."""
        degree = clamp01(distortion)
        return SessionRumor(
            session_id=session.id,
            region_id=deed.region_id,
            distorted_from_id=deed.id,
            distorted_from_kind="deed",
            statement=appraisal.retelling,
            distortion_degree=degree,
            support=clamp01(self._birth_support * (1.0 + appraisal.salience)),
            confidence=clamp01(1.0 - degree),
            origin_kind="deed",
            origin_deed_id=deed.id,
            origin_appraisal_id=appraisal.id,
            provenance=Provenance(source=SourceKind.SIMULATION, generated_by="deed:appraisal"),
        )

    def spread(
        self, session: GameSession, parent: SessionRumor, target: SpreadTarget
    ) -> SessionRumor | None:
        """One hop of a deed rumor: the parent's words distorted once more at the
        target's degree (one LLM call, BR-U6-18). None when the call failed."""
        chain = self._require_generator().generate_chain(
            source_text=parent.statement,
            source_id=parent.id,
            source_kind="rumor",
            source_confidence=parent.confidence,
            region_id=target.region_id,
            session_id=session.id,
            degrees=[target.degree],
            birth_support=target.support,
        )
        if not chain:
            return None
        return chain[0].model_copy(
            update={
                "origin_kind": "deed",
                "origin_deed_id": parent.origin_deed_id,
                "origin_appraisal_id": parent.origin_appraisal_id,
                "spread_from_region_id": target.from_region_id,
                "provenance": Provenance(source=SourceKind.SIMULATION, generated_by="llm:spread"),
            }
        )

    # -- internals -----------------------------------------------------------
    def _draft_for_region(
        self,
        session: GameSession,
        region_id: str,
        degrees: list[float],
        *,
        min_source_support: float | None = None,
        include_existing: bool = True,
    ) -> tuple[list[SessionRumor], bool]:
        """Generate a region's chains **without saving** (LLM happens here, so never
        inside a unit of work — BR-U4-14).

        Returns ``(drafts, complete)``. ``complete`` is False when any chain came back
        shorter than the degrees asked for, i.e. the provider failed part-way: callers
        that are about to delete something must not act on a partial result
        (code review U4-2 #6).
        """
        generator = self._require_generator()
        drafts: list[SessionRumor] = []
        complete = True
        for text, sid, kind, conf in self._collect_sources(
            session.world_id,
            region_id,
            session.id,
            min_source_support=min_source_support,
            include_existing=include_existing,
        ):
            chain = generator.generate_chain(
                source_text=text,
                source_id=sid,
                source_kind=kind,
                source_confidence=conf,
                region_id=region_id,
                session_id=session.id,
                degrees=degrees,
                birth_support=self._birth_support,
            )
            if len(chain) < len(degrees):
                # The generator swallows LLM errors and returns the successful prefix,
                # so a short chain is the only failure signal there is.
                complete = False
            drafts.extend(chain)
        return drafts, complete

    def _generate_for_region(
        self,
        session: GameSession,
        region_id: str,
        degrees: list[float],
        *,
        min_source_support: float | None = None,
        include_existing: bool = True,
    ) -> list[SessionRumor]:
        drafts, _complete = self._draft_for_region(
            session,
            region_id,
            degrees,
            min_source_support=min_source_support,
            include_existing=include_existing,
        )
        return self._repo.upsert_rumors(drafts) if drafts else []

    def _collect_sources(
        self,
        world_id: str,
        region_id: str,
        session_id: str,
        *,
        min_source_support: float | None = None,
        include_existing: bool = True,
        exclude_knowledge_ids: set[str] | frozenset[str] = frozenset(),
    ) -> list[tuple[str, str, str, float]]:
        """Sources = region direct + propagated canonical knowledge + existing
        session rumors (Q2). (text, id, kind, confidence).

        Canonical sources are never gated. When ``min_source_support`` is set, an
        existing rumor only re-seeds when ``support >= threshold`` (FR-H2 /
        BR-H1-7). ``list_rumors`` already excludes pruned rumors (BR-H1-6/11).
        ``include_existing=False`` seeds from canonical knowledge only — used by
        regenerate so preserved promoted rumors are NOT re-used as chain seeds
        (X3 review #1)."""
        snapshot = self._snapshots.get(world_id)
        if region_id not in snapshot.regions_by_id:
            raise LookupError(f"region not found: {region_id}")
        view = ConsensusEngine.from_snapshot(snapshot, self._params).resolve(region_id)
        sources: list[tuple[str, str, str, float]] = []
        for kv in view.direct + view.propagated:  # Q2: direct + propagated
            if kv.knowledge_id in exclude_knowledge_ids:  # U4 BR-U4-19: already seeded here
                continue
            sources.append((kv.statement, kv.knowledge_id, "knowledge", kv.confidence))
        if include_existing:
            for r in self._repo.list_rumors(session_id, region_id):  # existing rumors (chain)
                if r.origin_kind != "canonical":
                    # U6 (BR-U6-35): a deed rumor never seeds a canonical chain, so a void
                    # reaches everything the deed produced.
                    continue
                if min_source_support is not None and not rumor_dynamics.is_eligible_source(
                    r, min_support=min_source_support
                ):
                    continue
                sources.append((r.statement, r.id, "rumor", r.confidence))
        return sources

    def _chain_degrees(self, session_id: str, region_id: str) -> list[float]:
        return chain_degrees_for(self._repo.get_region_distortion(session_id, region_id))
