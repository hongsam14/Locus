"""SessionKnowledgeService — region knowledge inside a play session (FR-R5, FR-F5).

Result = canonical direct + inherited + global Knowledge (``region_known``,
dropping propagated + hearsay) overlaid with the session's active rumors:
promoted rumors appear direct-like (``scope_type=direct``, ``source="rumor:promoted"``),
other rumors are added as ``source="rumor"`` views (BR-S2-18/20). This is the
input for the play-layer NPC scope (U5) and the externally exposed session
region-knowledge API. No translation here: display localization is applied by
the API layer (FR-A2: play does not depend on localization).

U5: ``region_sources`` resolves a region's material once — static facts, hearsay and
active rumors, kept apart — and is the single consensus resolve behind three
consumers: the NPC scope, U4's player screen and the external ``QueryResult``
(design deviation 5). Hearsay is for the player screen only; the NPC scope never
receives it (deviation 1).
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.knowledge.consensus import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from locus.knowledge.query import region_known
from locus.play.models import SessionRumor
from locus.play.ports import SessionRumorStore
from locus.shared.models import KnowledgeView, LocusModel, QueryResult, ScopeType


class RegionSources(LocusModel):
    """One region's material inside a session (not U4's ``RegionView`` screen DTO)."""

    world_id: str
    region_id: str
    facts: list[KnowledgeView]  # region_known(view): direct + inherited + global
    hearsay: list[KnowledgeView]  # the player screen only — never an NPC's knowledge
    rumors: list[SessionRumor]  # the region's active session rumors


class SessionKnowledgeService:
    def __init__(
        self,
        repo: SessionRumorStore,
        snapshots: SnapshotSource,
        params: ConsensusParams = DEFAULT_PARAMS,
    ) -> None:
        self._repo = repo
        self._snapshots = snapshots
        self._params = params

    def region_sources(self, session_id: str, region_id: str) -> RegionSources:
        """The region's facts, hearsay and active rumors, resolved once (BLM §1.1)."""
        session = self._repo.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        snapshot = self._snapshots.get(session.world_id)
        if region_id not in snapshot.regions_by_id:
            raise LookupError(f"region not found: {region_id}")
        view = ConsensusEngine.from_snapshot(snapshot, self._params).resolve(region_id)
        return RegionSources(
            world_id=session.world_id,
            region_id=region_id,
            facts=region_known(view),  # direct + inherited + global (FR-R5.1)
            hearsay=list(view.hearsay),
            rumors=self._repo.list_rumors(session_id, region_id),
        )

    def knowledge_for_region(self, session_id: str, region_id: str) -> QueryResult:
        src = self.region_sources(session_id, region_id)
        promoted = [_rumor_view(r) for r in src.rumors if r.promoted]
        other = [_rumor_view(r) for r in src.rumors if not r.promoted]

        items = src.facts + promoted + other
        # unique = region-specific (direct) + promoted rumors (direct-like);
        # shared = inherited + global. Non-promoted rumors are supplementary.
        direct = ScopeType.DIRECT.value
        shared_scopes = (ScopeType.INHERITED.value, ScopeType.GLOBAL.value)
        unique_ids = [k.knowledge_id for k in src.facts if str(k.scope_type) == direct]
        unique_ids += [v.knowledge_id for v in promoted]
        shared_ids = [k.knowledge_id for k in src.facts if str(k.scope_type) in shared_scopes]
        return QueryResult(
            world_id=src.world_id,
            region_id=region_id,
            items=items,
            shared_ids=shared_ids,
            unique_ids=unique_ids,
        )


def is_rumor_view(view: KnowledgeView) -> bool:
    """Whether a ``KnowledgeView`` came from a session rumor (vs canonical knowledge)."""
    return (view.source or "").startswith("rumor")


def _rumor_view(r: SessionRumor) -> KnowledgeView:
    """A session rumor as a direct-like KnowledgeView (source ``rumor`` / ``rumor:promoted``)."""
    return KnowledgeView(
        knowledge_id=r.id,
        statement=r.statement,
        scope_type=ScopeType.DIRECT.value,
        is_hearsay=False,
        confidence=r.confidence,
        distortion=r.distortion_degree,
        source="rumor:promoted" if r.promoted else "rumor",
        region_id=r.region_id,
    )
