"""PlayService — the player's perspective (U4; BLM §3, FR-C5/C6).

Read side: ``current_region`` assembles one ``RegionView`` from the canonical
snapshot (consensus, hierarchy path, NPCs, move options) plus the session's
active rumors — read-only, no writes on GET (BR-U4-4). Write side: ``act``
pre-validates the action for a friendly 400 and hands it to
``TurnAdvancer.begin`` (the authoritative check happens under the guard).
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.knowledge.consensus import DEFAULT_PARAMS, ConsensusEngine, ConsensusParams
from locus.knowledge.query import level_path, region_known
from locus.play.base import SessionAppService
from locus.play.errors import InvalidActionError
from locus.play.models import Player, PlayerAction, RegionView, TimelineEntry, TurnRun
from locus.play.player import movement
from locus.play.ports import PlayRepository
from locus.play.turn.advancer import TurnAdvancer
from locus.play.turn.guard import TurnGuard
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import WorldSnapshot


class PlayService(SessionAppService):
    def __init__(
        self,
        repo: PlayRepository,
        snapshots: SnapshotSource,
        params: ConsensusParams = DEFAULT_PARAMS,
        *,
        guard: TurnGuard,
        turns: TurnAdvancer,
        tuning: PlayTuning,
    ) -> None:
        super().__init__(repo)
        self._snapshots = snapshots
        self._params = params
        self._guard = guard
        self._turns = turns
        self._tuning = tuning

    # -- reads ---------------------------------------------------------------
    def player(self, session_id: str) -> Player:
        self._require_session(session_id)
        player = self._repo.get_player(session_id)
        if player is None:
            raise LookupError(f"session has no player: {session_id}")
        return player

    def current_region(self, session_id: str) -> RegionView:
        """Everything the player screen shows (BR-U4-22). 400 without a player,
        404 when the player's region no longer exists (NFR-9)."""
        session = self._require_session(session_id)
        player = self._require_player(session_id)
        snapshot = self._snapshots.get(session.world_id)
        region = snapshot.regions_by_id.get(player.region_id)
        if region is None:
            raise LookupError(f"player region no longer exists: {player.region_id}")
        view = ConsensusEngine.from_snapshot(snapshot, self._params).resolve(region.id)
        return RegionView(
            session_id=session.id,
            turn=session.turn,
            player=player,
            region_id=region.id,
            region_name=region.name,
            level=str(region.level),
            description=region.description or "",
            level_path=level_path(region, snapshot),
            npcs=list(snapshot.npcs_by_region.get(region.id, [])),
            facts=region_known(view),
            hearsay=list(view.hearsay),
            rumors=self._repo.list_rumors(session.id, region.id),
            moves=movement.move_options(snapshot, region.id, self._tuning),
            turn_running=self._guard.is_running(session.id),
            llm_available=self._turns.llm_available,
        )

    def turn_run(self, session_id: str, run_id: str) -> TurnRun:
        self._require_session(session_id)
        run = self._repo.get_run(session_id, run_id)
        if run is None:  # also when the run belongs to another session (NFR R-06)
            raise LookupError(f"turn run not found: {run_id}")
        return run

    def list_runs(self, session_id: str, status: str | None = None) -> list[TurnRun]:
        self._require_session(session_id)
        return self._repo.list_runs(session_id, status)

    def log(self, session_id: str) -> list[TimelineEntry]:
        """The whole session timeline (U4 "basic"; the player filter is U7)."""
        self._require_session(session_id)
        return self._repo.list_timeline(session_id)

    # -- actions -------------------------------------------------------------
    def act(self, session_id: str, action: PlayerAction) -> TurnRun:
        """Validate for a friendly 400, then start the run (202). The turn engine
        re-validates under the guard against the fresh position (FD R-10)."""
        session = self._require_open(session_id)
        player = self._require_player(session_id)
        snapshot: WorldSnapshot = self._snapshots.get(session.world_id)
        movement.validate_action(snapshot, player, action, self._tuning)
        return self._turns.begin(session_id, action)

    # -- internals -----------------------------------------------------------
    def _require_player(self, session_id: str) -> Player:
        player = self._repo.get_player(session_id)
        if player is None:
            raise InvalidActionError(f"session has no player: {session_id}")
        return player
