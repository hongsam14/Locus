"""SessionQueryEngine — NPC knowledge in a session context (S2, FR-R5).

Result = canonical direct+inherited+global Knowledge (via ``canonical_known``,
dropping propagated + auto-rumor) overlaid with the session's rumors: promoted
rumors appear direct-like (``scope_type=direct``, ``is_rumor=True``), other
rumors are added as rumor views (BR-S2-18/20). The canonical ``QueryEngine`` is
untouched (NFR-R6).
"""

from __future__ import annotations

from ..consensus.engine import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from ..models import KnowledgeView, QueryResult, ScopeType
from ..query.engine import canonical_known
from ..query.loader import WorldLoader
from .models import SessionRumor
from .repository import SessionRepository


class SessionQueryEngine:
    def __init__(
        self,
        repo: SessionRepository,
        loader: WorldLoader,
        params: ConsensusParams = DEFAULT_PARAMS,
    ) -> None:
        self._repo = repo
        self._loader = loader
        self._params = params

    def knowledge_for_region(self, session_id: str, region_id: str) -> QueryResult:
        session = self._repo.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        kg, topo = self._loader.load(session.world_id)
        if region_id not in {r.id for r in topo.regions}:
            raise LookupError(f"region not found: {region_id}")
        view = ConsensusEngine(kg, topo, self._params).resolve(region_id)

        canonical = canonical_known(view)  # direct + inherited + global (FR-R5.1)
        rumors = self._repo.list_rumors(session_id, region_id)
        promoted = [_rumor_view(r) for r in rumors if r.promoted]
        other = [_rumor_view(r) for r in rumors if not r.promoted]

        items = canonical + promoted + other
        # unique = region-specific (direct) + promoted rumors (direct-like);
        # shared = inherited + global. Non-promoted rumors are supplementary.
        unique_ids = [v.knowledge_id for v in view.direct] + [v.knowledge_id for v in promoted]
        shared_ids = [v.knowledge_id for v in view.inherited + view.global_knowledge]
        return QueryResult(
            world_id=session.world_id,
            region_id=region_id,
            items=items,
            shared_ids=shared_ids,
            unique_ids=unique_ids,
        )


def _rumor_view(r: SessionRumor) -> KnowledgeView:
    """A session rumor as a direct-like KnowledgeView, flagged is_rumor (Q6=A)."""
    return KnowledgeView(
        knowledge_id=r.id,
        statement=r.statement,
        scope_type=ScopeType.DIRECT.value,
        is_rumor=True,
        confidence=r.confidence,
        distortion_degree=r.distortion_degree,
        source="session-rumor",
        region_id=r.region_id,
    )
