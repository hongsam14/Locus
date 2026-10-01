"""TurnAdvancer — the turn engine's single entry point (Phase 2 FR-P3.3; U4 AD-R5=B).

One turn = three phases (U4, BLM §4.3; BR-U4-14):

1. **compute** — apply ACTIVE events to per-region distortion *in memory*
   (deterministic, no writes);
2. **draft** — ask ``RumorService.append_for_turn`` for new rumors per target
   region at the post-event distortion, under the turn's ``LlmBudget`` and the
   per-region caps (LLM calls happen here, outside any transaction);
3. **store** — one unit of work: event updates, distortions, drafts, rumor→region
   feedback, support evolution / decay / prune / promotion, batch upsert, turn
   bump and the timeline entries.

``advance(session_id, action=None)`` runs an action's turns synchronously and
returns an ``ActionResult`` (P7; the GM manual turn passes ``None``);
``begin(session_id, action)`` records the action, hands the turn loop to the
``TurnExecutor`` and returns the ``TurnRun`` at once (Q4=A). One run per session
at a time (``TurnGuard``, BR-U4-13). Validation of a move happens under the
guard against the player's *current* position (FD R-10).
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from pydantic import Field

from locus.knowledge.cache import SnapshotSource
from locus.knowledge.propagation import best_path_weights
from locus.play.base import (  # noqa: F401  (re-exported)
    SessionAppService,
    SessionClosedError,
    names_of,
    region_name,
    where,
)
from locus.play.errors import InvalidActionError, TurnInProgressError  # noqa: F401
from locus.play.event import dynamics
from locus.play.gm import narrator as gm_narrator
from locus.play.models import (
    DEFAULT_DISTORTION_DEGREE,
    ActionResult,
    DeclareAction,
    DeedAppraisal,
    EndTalkAction,
    EventStatus,
    GameSession,
    MoveAction,
    Narration,
    Player,
    PlayerAction,
    SceneBrief,
    SessionEvent,
    SessionRumor,
    SpreadTarget,
    TimelineEntry,
    TimelineKind,
    TurnResult,  # noqa: F401  (re-exported: lives in models since U4)
    TurnRun,
    TurnRunStatus,
    WaitAction,
)
from locus.play.npc.scope import pick_facts, pick_rumors, shadowed_sources
from locus.play.player import movement
from locus.play.ports import PlayRepository
from locus.play.rumor import dynamics as rumor_dynamics
from locus.play.rumor import promotion
from locus.play.rumor.dynamics import DEFAULT_RUMOR_DYNAMICS
from locus.play.rumor.feedback import RumorFeedbackService
from locus.play.rumor.service import SKIP_BUDGET, SKIP_CAPPED, SKIP_LLM_FAILED, RumorService
from locus.play.rumor.spread import neighbour_map, passable_both_ways, plan_spread
from locus.play.turn.budget import LlmBudget
from locus.play.turn.changes import shape_region_changes
from locus.play.turn.executor import SyncTurnExecutor, TurnExecutor
from locus.play.turn.guard import TurnGuard
from locus.play.turn.quota import RegionQuota
from locus.play.turn.summary import merge_changes, narrate, scope_changes
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import NPC, LocusModel, Region, WorldSnapshot

if TYPE_CHECKING:  # wired by assemble_play; imported for types only (no cycles)
    from locus.play.deeds.service import DeedService
    from locus.play.gm.narrator import GmNarrator
    from locus.play.npc.dialogue import NpcDialogueService
    from locus.play.region_knowledge import SessionKnowledgeService

logger = logging.getLogger(__name__)

RUN_FAILED_MESSAGE = "turn processing failed"  # fixed one-liner (NFR-6)


class _EventApplication(LocusModel):
    """Outcome of applying ACTIVE events for one turn — computed in memory; the
    turn's unit of work persists ``event_updates`` / ``distortions`` / ``timeline``."""

    applied_ids: list[str] = Field(default_factory=list)
    resolved_ids: list[str] = Field(default_factory=list)
    # primary target regions of applied events (where rumors are drafted next)
    target_regions: set[str] = Field(default_factory=set)
    # every region whose distortion moved (drives support auto-evolution)
    influenced_regions: set[str] = Field(default_factory=set)
    # event id -> primary region id (for X1 region_changes shaping)
    event_regions: dict[str, str] = Field(default_factory=dict)
    # post-event distortion per region row read (U4; feeds the rumor drafts)
    distortions: dict[str, float] = Field(default_factory=dict)
    event_updates: list[SessionEvent] = Field(default_factory=list)
    timeline: list[TimelineEntry] = Field(default_factory=list)


class _Prep(LocusModel):
    """What an action's prep step produced before its first turn (U6 BLM §0.1)."""

    declaration: Narration | None = None
    llm_failed: bool = False


# Facts / rumors a narration may look at (BR-U6-26): one limit, the narrator's (C8).
SCENE_FACTS = gm_narrator.FACTS_MAX
SCENE_RUMORS = gm_narrator.RUMORS_MAX


class TurnAdvancer(SessionAppService):
    """Advance a session by composing the rumor / event / distortion steps."""

    def __init__(
        self,
        repo: PlayRepository,
        snapshots: SnapshotSource,
        rumors: RumorService | None,
        feedback: RumorFeedbackService,
        params: PlayTuning = DEFAULT_RUMOR_DYNAMICS,
        *,
        guard: TurnGuard | None = None,
        executor: TurnExecutor | None = None,
        deeds: DeedService | None = None,
        dialogue: NpcDialogueService | None = None,
        narrator: GmNarrator | None = None,
        region_knowledge: SessionKnowledgeService | None = None,
        default_lang: str = "ko",
    ) -> None:
        super().__init__(repo)
        self._snapshots = snapshots
        self._rumors = rumors  # None without an LLM provider: drafts are skipped (Q6)
        self._feedback = feedback
        self._params = params
        self._guard = guard if guard is not None else TurnGuard()
        self._executor = executor if executor is not None else SyncTurnExecutor()
        # U6 — each optional: None turns its part off (no deeds / no appraisal / the
        # fallback narration / a scene without facts and rumors), so U4-era callers that
        # build the engine directly keep working (code-plan review R-07).
        self._deeds = deeds
        self._dialogue = dialogue
        self._narrator = narrator
        self._region_knowledge = region_knowledge
        self._default_lang = default_lang

    @property
    def llm_available(self) -> bool:
        return self._rumors is not None and self._rumors.llm_available

    @property
    def guard(self) -> TurnGuard:
        return self._guard

    # -- entry points --------------------------------------------------------
    def advance(
        self,
        session_id: str,
        action: PlayerAction | None = None,
        *,
        promotion_threshold: float | None = None,
        lang: str | None = None,
    ) -> ActionResult:
        """Run the action's turns synchronously (P7). ``None`` = GM manual turn (1)."""
        run = self._start(session_id, action, lang=lang)
        try:
            result = self._run_turns(run, promotion_threshold=promotion_threshold)
            self._finish(run, result)
            return result
        except Exception as exc:
            self._fail(run, exc)
            raise
        finally:
            self._guard.release(session_id)

    def begin(
        self,
        session_id: str,
        action: PlayerAction | None,
        *,
        promotion_threshold: float | None = None,
        lang: str | None = None,
    ) -> TurnRun:
        """Record the action at once and run its turns in the background (Q4=A)."""
        run = self._start(session_id, action, lang=lang)
        try:
            self._executor.submit(self._run, run.id, session_id, promotion_threshold)
        except BaseException as exc:  # e.g. executor shut down (FD R-11)
            # Release in a `finally`: a failing failure-recorder used to leak the guard
            # and brick the session for the process lifetime (code review U4-2 #2).
            try:
                self._fail(run, exc)
            except Exception:
                logger.exception("could not record the failed start of turn run %s", run.id)
            finally:
                self._guard.release(session_id)
            raise
        return run

    # -- run lifecycle -------------------------------------------------------
    def _start(
        self, session_id: str, action: PlayerAction | None, *, lang: str | None = None
    ) -> TurnRun:
        """Guard + validate against the current position + immediate state (BLM §4.1)."""
        session = self._require_open(session_id)
        run = TurnRun(session_id=session_id, action=action, started_turn=session.turn)
        if isinstance(action, DeclareAction):
            run.lang = lang  # the narration's language (U6, FD review R-17)
        self._guard.acquire(session_id, run.id)  # TurnInProgressError -> 409
        try:
            # Read again under the guard: a turn committed between the read above and
            # the acquire would otherwise be counted as this run's (U6 review #8).
            session = self._require_open(session_id)
            run.started_turn = session.turn
            # The world is read under the guard too: an editor region delete holds the
            # leases while it writes, so a snapshot read before the acquire could move the
            # player into a region deleted in between (U3 review #11).
            snapshot = self._snapshots.get(session.world_id)
            player = self._repo.get_player(session_id)
            option = None
            if action is not None:
                if player is None:
                    raise InvalidActionError("session has no player")
                # also the declaration rule (BR-U6-5), so `act` answers 400 before the
                # guard and this re-check holds the same rule (U6 review #14)
                option = movement.validate_action(snapshot, player, action, self._params)
            run.cost_turns = movement.action_cost(action, option)
            with self._repo.uow() as u:
                if player is not None and action is not None:
                    # One charge for every player action: its turn cost (U6 review C7).
                    from_id = player.region_id
                    run.turns_charged = run.cost_turns
                    player.turns_spent += run.cost_turns
                    if isinstance(action, MoveAction):
                        # Remembered so a failed run can put the player back: the
                        # immediate state commits in its own transaction, independent of
                        # the turn loop (code review U4-2 #5).
                        run.from_region_id = from_id
                        player.region_id = action.to_region_id
                    u.players.update_player(player)
                    if isinstance(action, MoveAction):
                        to_id = action.to_region_id
                        names = names_of(snapshot)
                        arrival = (  # U6: the arrival is a deed (BR-U6-1); a failed run
                            # with no turn advanced deletes it again (BR-U6-36)
                            self._deeds.arrival(
                                u,
                                session,
                                player,
                                snapshot.regions_by_id[to_id],
                                snapshot,
                                run_id=run.id,
                            )
                            if self._deeds is not None
                            else None
                        )
                        u.timeline.append_timeline(
                            self._entry(
                                session,
                                TimelineKind.PLAYER_MOVED,
                                f"{player.name} → {region_name(names, to_id)}",
                                {
                                    "player_id": player.id,
                                    "from_region_id": from_id,
                                    "from_region_name": region_name(names, from_id),
                                    "to_region_id": to_id,
                                    "to_region_name": region_name(names, to_id),
                                    "region_id": to_id,
                                    "region_name": region_name(names, to_id),
                                    "cost_turns": run.cost_turns,
                                    "deed_id": arrival.id if arrival is not None else None,
                                },
                            )
                        )
                    elif isinstance(action, WaitAction):
                        rname = snapshot.regions_by_id[player.region_id].name
                        u.timeline.append_timeline(
                            self._entry(
                                session,
                                TimelineKind.PLAYER_WAITED,
                                f"{player.name} waits in {rname}",
                                {
                                    "player_id": player.id,
                                    "region_id": player.region_id,
                                    "region_name": rname,
                                },
                            )
                        )
                    elif isinstance(action, EndTalkAction):  # closes a conversation (U5)
                        region = snapshot.regions_by_id[player.region_id]
                        # validate_action above (under the guard) guaranteed the NPC is
                        # here, so there is no fallback name (U5 review C4)
                        npc = next(
                            n
                            for n in movement.npcs_here(snapshot, region.id)
                            if n.id == action.npc_id
                        )
                        npc_name = npc.name
                        said = u.conversations.message_counts(session_id)  # U5 C1
                        u.timeline.append_timeline(
                            self._entry(
                                session,
                                TimelineKind.NPC_TALKED,
                                f"{player.name} spoke with {npc_name}",
                                {
                                    "npc_id": action.npc_id,
                                    "npc_name": npc_name,
                                    "region_id": region.id,
                                    "region_name": region.name,
                                    "messages": said.get(action.npc_id, 0),
                                },
                            )
                        )
                run = u.runs.create_run(run)
        except BaseException:
            self._guard.release(session_id)
            raise
        return run

    def _run(self, run_id: str, session_id: str, promotion_threshold: float | None) -> None:
        """Background body (``begin``): never raises; the run records its outcome.

        Everything — including reading the run row back — sits inside the try/finally.
        A transient repository failure on that read used to escape before the guard was
        released, so the session answered 409 to every action and could not even be
        closed for the rest of the process (code review U4-2 #1).
        """
        try:
            run = self._repo.get_run(session_id, run_id)
            if run is None:  # pragma: no cover - defensive
                return
            try:
                result = self._run_turns(run, promotion_threshold=promotion_threshold)
                self._finish(run, result)
            except Exception as exc:
                logger.exception("turn run %s failed", run_id)
                try:
                    self._fail(run, exc)
                except Exception:  # pragma: no cover - storage down: nothing to record
                    logger.exception("could not record failure of turn run %s", run_id)
        except BaseException:
            logger.exception("turn run %s could not be started", run_id)
        finally:
            self._guard.release(session_id)

    def _run_turns(self, run: TurnRun, *, promotion_threshold: float | None) -> ActionResult:
        # None = the tuned bar (U7, FR-A7); a caller may still pass its own
        threshold = (
            promotion_threshold
            if promotion_threshold is not None
            else self._params.promotion_threshold
        )
        results: list[TurnResult] = []
        used, exhausted, failed = 0, False, False
        prep = _Prep()
        for i in range(run.cost_turns):
            # Re-check OPEN at every turn boundary: `close_session`'s idle check is a
            # check, not a lock, so a session closed in the gap (or by the CLI, which
            # cannot share this process's guard) must stop the loop instead of writing
            # rumors and turns into a closed session (code review U4-2 #11).
            session = self._require_open(run.session_id)
            budget = LlmBudget(self._params.max_llm_calls_per_turn)
            if i == 0:
                # U6 (BLM §0.1): narration / appraisal before turn 1, reserved first from
                # turn 1's budget (Q2=A). A failed prep call trips this turn's breaker.
                prep = self._prepare(run, session, budget)
            tr = self._one_turn(session, budget, threshold, llm_failed=i == 0 and prep.llm_failed)
            results.append(tr)
            used += tr.llm_calls
            exhausted |= tr.budget_exhausted
            failed |= tr.llm_failed
        session = self._require_session(run.session_id)  # summary may read a closed session
        player = self._repo.get_player(run.session_id)
        snapshot = self._snapshots.get(session.world_id)
        changes = scope_changes(
            merge_changes(results), snapshot, player.region_id if player else None
        )
        return ActionResult(
            session=session,
            player=player,
            turns=results,
            changes=changes,
            narration=narrate(changes),
            llm_calls=used,
            budget_exhausted=exhausted,
            llm_failed=failed or prep.llm_failed,
            llm_available=self.llm_available,
            declaration=prep.declaration,
        )

    # -- U6 prep step (BLM §0.1, §2.2, §3.2) -----------------------------------
    def _prepare(self, run: TurnRun, session: GameSession, budget: LlmBudget) -> _Prep:
        """The LLM work an action needs before its turn, outside any transaction."""
        action = run.action
        if not isinstance(action, (DeclareAction, EndTalkAction)):
            return _Prep()
        player = self._repo.get_player(session.id)
        snapshot = self._snapshots.get(session.world_id)
        region = snapshot.regions_by_id.get(player.region_id) if player is not None else None
        if player is None or region is None:
            return _Prep()
        if isinstance(action, DeclareAction):
            return self._narrate(run, session, player, region, snapshot, action, budget)
        if self._dialogue is None or self._deeds is None:
            return _Prep()
        npc = movement.find_npc(snapshot, action.npc_id)
        if npc is None:
            return _Prep()
        outcome = self._dialogue.appraise(session, player, npc, snapshot, budget=budget)
        if outcome.llm_calls and not outcome.llm_failed:
            self._deeds.record_appraisal(run, session, player, region, npc, outcome)
        return _Prep(llm_failed=outcome.llm_failed)

    def _narrate(
        self,
        run: TurnRun,
        session: GameSession,
        player: Player,
        region: Region,
        snapshot: WorldSnapshot,
        action: DeclareAction,
        budget: LlmBudget,
    ) -> _Prep:
        declared = action.text.strip()
        lang = run.lang or self._default_lang
        failed = False
        if self._narrator is None or budget.exhausted:  # no LLM, or a zero budget (R-04)
            narration = gm_narrator.fallback(
                declaration=declared, player_name=player.name, lang=lang
            )
        else:
            # Read before the call is booked and outside its `try`: a storage error here
            # is the run's failure, not the LLM's (U6 review #9).
            scene = self._scene(session, player, region, snapshot)
            budget.take(1)
            try:
                narration = self._narrator.narrate(declaration=declared, scene=scene, lang=lang)
            except Exception:
                logger.exception("narration failed for run %s", run.id)
                narration = gm_narrator.fallback(
                    declaration=declared, player_name=player.name, lang=lang, llm_calls=1
                )
                failed = True
        if self._deeds is not None:
            self._deeds.record_declaration(
                run,
                session,
                player,
                region,
                movement.npcs_here(snapshot, region.id),
                narration,
                declared,
            )
        return _Prep(declaration=narration, llm_failed=failed)

    def _scene(
        self, session: GameSession, player: Player, region: Region, snapshot: WorldSnapshot
    ) -> SceneBrief:
        """This region only: name, description, people, a few facts and rumors (BR-U6-26)."""
        facts: list = []
        rumors: list[SessionRumor] = []
        if self._region_knowledge is not None:
            src = self._region_knowledge.region_sources(
                session.id, region.id, session=session, snapshot=snapshot
            )
            # The same source hiding as an NPC's context (BR-U5-11): the narration's record
            # becomes deed text that NPCs remember and retell (U6 review #1).
            rumors = pick_rumors(src.rumors, SCENE_RUMORS)
            hidden = shadowed_sources(rumors, [*src.rumors, *src.lineage])
            facts = pick_facts(src.facts, SCENE_FACTS, hidden=hidden)
        return SceneBrief(
            player_name=player.name,
            region_name=region.name,
            description=region.description or "",
            npcs=movement.npcs_here(snapshot, region.id),
            facts=facts,
            rumors=rumors,
        )

    def _finish(self, run: TurnRun, result: ActionResult) -> None:
        with self._repo.uow() as u:
            run.status = TurnRunStatus.DONE
            run.result = result
            run.finished_at = datetime.now(timezone.utc)
            u.runs.update_run(run)

    def _fail(self, run: TurnRun, exc: BaseException) -> None:
        """Mark the run failed, undo the immediate state the turns never paid for, and
        keep only the exception class in the timeline (NFR-6).

        The move and the turn charge commit in their own transaction before the loop
        starts (Q4=A), so without compensation a failing loop left the player moved and
        charged while the world clock stood still — repeatable for free movement
        (code review U4-2 #5). Turns that did advance are kept; the charge is reduced
        to them and the position is restored only when no turn advanced at all.
        """
        advanced = self._advanced_turns(run)
        with self._repo.uow() as u:
            run.status = TurnRunStatus.FAILED
            run.error = RUN_FAILED_MESSAGE
            run.finished_at = datetime.now(timezone.utc)
            u.runs.update_run(run)
            player = u.players.get_player(run.session_id)
            restored_region_id: str | None = None
            if player is not None and run.turns_charged:
                refund = max(0, run.turns_charged - advanced)
                if refund:
                    player.turns_spent = max(0, player.turns_spent - refund)
                    if advanced == 0 and run.from_region_id is not None:
                        player.region_id = run.from_region_id  # the move never happened
                        restored_region_id = player.region_id
                    u.players.update_player(player)
            if advanced == 0 and self._deeds is not None:
                # U6 (BR-U6-36): the run never happened, so neither did its deeds — the
                # arrival of an undone move, a declaration, a talk's statement and their
                # appraisals. Their timeline lines stay as an audit trail (N6-4).
                u.deeds.delete_by_run(run.session_id, run.id)
            session = u.sessions.get_session(run.session_id)
            if session is not None:
                u.timeline.append_timeline(
                    self._entry(
                        session,
                        TimelineKind.TURN_RUN_FAILED,
                        RUN_FAILED_MESSAGE,
                        {
                            "run_id": run.id,
                            "error_type": type(exc).__name__,
                            "turns_advanced": advanced,
                            "turns_refunded": max(0, run.turns_charged - advanced),
                            # where the player stands again — the player log follows it
                            # (U7 review #5, BR-U7-13)
                            "restored_region_id": restored_region_id,
                        },
                    )
                )

    def _advanced_turns(self, run: TurnRun) -> int:
        """How many turns of this run actually committed (each turn is its own UoW)."""
        session = self._repo.get_session(run.session_id)
        if session is None:  # pragma: no cover - defensive
            return 0
        return max(0, min(run.cost_turns, session.turn - run.started_turn))

    # -- one turn ------------------------------------------------------------
    def _one_turn(
        self,
        session: GameSession,
        budget: LlmBudget,
        promotion_threshold: float,
        *,
        llm_failed: bool = False,
    ) -> TurnResult:
        """Compute -> draft -> store (BLM §4.3). Step order inside the store phase is
        the pre-U4 sequence: feedback → reinforce/decay → prune → promotion
        (BR-H1-12) → batch upsert → bump."""
        snapshot = self._snapshots.get(session.world_id)

        # (a) compute: ACTIVE events -> post-event distortion, in memory
        events = self._compute_events(session, snapshot)
        names = names_of(snapshot)  # FR-D3: lines carry names

        # (b) draft: new rumors per target region at the post-event distortion,
        #     under the turn budget and the per-region caps (LLM, outside any UoW)
        drafts: dict[str, list] = {}
        skipped: list[str] = []
        capped: list[str] = []
        rumor_service = self._rumors
        # One quota for seeds, spread and canonical drafts (U6 BR-U6-15, TP-U6-8).
        quota = RegionQuota(
            Counter(r.region_id for r in self._repo.list_rumors(session.id)),
            self._params.max_active_rumors_per_region,
        )
        # (b1) deed seeds — no LLM (BR-U6-14)
        seeds = self._draft_seeds(session, snapshot, events, quota)
        # (b2) deed spread — before canonical drafts in the budget (Q2=A, BR-U6-21)
        spreads, llm_failed = self._draft_spread(
            session, snapshot, budget, quota, seeds, llm_failed=llm_failed
        )
        # (b3) canonical drafts with what is left of the budget
        if rumor_service is not None and rumor_service.llm_available:
            # Q6: without a provider the deterministic steps still run
            for region_id in sorted(events.target_regions):
                if region_id not in snapshot.regions_by_id:
                    # The region was edited out of the canonical world after the event
                    # was created. Drafting would raise every turn and wedge the engine
                    # for the whole session (code review U4-2 #4); skip it instead.
                    skipped.append(region_id)
                    continue
                if llm_failed or budget.exhausted:
                    skipped.append(region_id)
                    continue
                # every event target is a key of `events.distortions`; a region without a
                # stored row is at the default (U7 review C9)
                distortion = events.distortions.get(region_id, DEFAULT_DISTORTION_DEGREE)
                new, reason = rumor_service.append_for_turn(
                    session,
                    region_id,
                    distortion=distortion,
                    budget=budget,
                    max_new=self._params.max_new_rumors_per_region_turn,
                    max_active=self._params.max_active_rumors_per_region,
                    min_source_support=self._params.min_source_support,
                    reserved=quota.reserved(region_id),
                )
                if new:
                    drafts[region_id] = new
                    quota.add(region_id, len(new))
                if reason == SKIP_CAPPED:
                    capped.append(region_id)
                elif reason == SKIP_BUDGET:
                    skipped.append(region_id)
                elif reason == SKIP_LLM_FAILED:  # circuit breaker (NFR R-02)
                    llm_failed = True

        # (c) store: one unit of work
        with self._repo.uow() as u:
            for ev in events.event_updates:
                try:
                    u.events.update_event(ev)
                except KeyError:
                    # Discarded by the GM during this turn's LLM window: writing it back
                    # would resurrect it (code review U4-2 #9).
                    logger.info("event %s vanished during the turn; not re-created", ev.id)
            # Only the regions the events actually moved. Rewriting every row from the
            # map read before the multi-second LLM phase silently overwrote a concurrent
            # GM distortion edit and cost one upsert per region per turn
            # (code review U4-2 #8).
            for rid in sorted(events.influenced_regions):  # each is a key (C9)
                u.distortions.set_region_distortion(session.id, rid, events.distortions[rid])
            for entry in events.timeline:
                u.timeline.append_timeline(entry)
            added_by_region: dict[str, list[str]] = {}
            for region_id, new_rumors in drafts.items():
                u.rumors.upsert_rumors(new_rumors)
                added_by_region[region_id] = [r.id for r in new_rumors]
            newborn_deed_ids = self._store_deed_rumors(u, session, snapshot, seeds, spreads)
            for r in [rumor for _ap, rumor in seeds] + [rumor for rumor, _t in spreads]:
                added_by_region.setdefault(r.region_id, []).append(r.id)

            rumors = u.rumors.list_rumors(session.id)  # ACTIVE only (BR-H1-6/11)
            feedback = self._feedback.apply_feedback(session, rumors, store=u.distortions)
            # U7 (BR-U7-4, Q4=A): only an event exempts a region from decay. Feedback
            # regions decay too, so their strong rumors fade and the share is given back.
            reinforced = set(events.influenced_regions)
            if events.influenced_regions:
                dynamics.evolve_support(
                    rumors,
                    events.influenced_regions,
                    reinforce=self._params.event_support_reinforce,
                )
            # newborn deed rumors skip this turn's decay — per rumor, not per region (R-15)
            rumor_dynamics.decay_support(
                rumors, reinforced, decay=self._params.support_decay, exempt_ids=newborn_deed_ids
            )
            survivors, prunable = rumor_dynamics.partition_prunable(
                rumors, floor=self._params.prune_floor
            )
            for r in prunable:
                r.active = False
                u.timeline.append_timeline(
                    self._entry(
                        session,
                        TimelineKind.PRUNE,
                        f"pruned a rumor in {region_name(names, r.region_id)}",
                        {"rumor_id": r.id, **where(names, r.region_id)},
                    )
                )
            res = promotion.evaluate(survivors, promotion_threshold)
            promoted = set(res.promoted_ids)
            demoted = set(res.demoted_ids)
            for r in survivors:
                if r.id in promoted:
                    r.promoted = True
                    u.timeline.append_timeline(
                        self._entry(
                            session,
                            TimelineKind.PROMOTE,
                            f"promoted a rumor in {region_name(names, r.region_id)}",
                            {"rumor_id": r.id, **where(names, r.region_id)},
                        )
                    )
                elif r.id in demoted:
                    r.promoted = False
                    u.timeline.append_timeline(
                        self._entry(
                            session,
                            TimelineKind.DEMOTE,
                            f"demoted a rumor in {region_name(names, r.region_id)}",
                            {"rumor_id": r.id, **where(names, r.region_id)},
                        )
                    )
            u.rumors.upsert_rumors(rumors)  # batch (FR-H5 / BR-H1-13)
            new_turn = u.sessions.bump_turn(session.id)
            pruned_ids = [r.id for r in prunable]
            feedback_regions = sorted(feedback.strong_regions)
            rumor_region = {r.id: r.region_id for r in rumors}
            region_changes = shape_region_changes(
                promoted=res.promoted_ids,
                demoted=res.demoted_ids,
                pruned=pruned_ids,
                applied_events=events.applied_ids,
                resolved_events=events.resolved_ids,
                added_by_region=added_by_region,
                rumor_region=rumor_region,
                event_region=events.event_regions,
                region_names={r.id: r.name for r in snapshot.topo.regions},
            )
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.ADVANCE_TURN,
                    f"advanced to turn {new_turn}",
                    {
                        "applied": events.applied_ids,
                        "resolved": events.resolved_ids,
                        "promoted": res.promoted_ids,
                        "demoted": res.demoted_ids,
                        "pruned": pruned_ids,
                        "feedback_regions": feedback_regions,
                        "feedback_restored_regions": sorted(feedback.restored),
                        "llm_calls": budget.used,
                    },
                    turn=new_turn,
                )
            )
        return TurnResult(
            session_id=session.id,
            turn=new_turn,
            promoted_ids=res.promoted_ids,
            demoted_ids=res.demoted_ids,
            applied_event_ids=events.applied_ids,
            resolved_event_ids=events.resolved_ids,
            pruned_rumor_ids=pruned_ids,
            feedback_regions=feedback_regions,
            region_changes=region_changes,
            llm_calls=budget.used,
            budget_exhausted=budget.exhausted,
            llm_failed=llm_failed,
            rumors_skipped_regions=skipped,
            rumors_capped_regions=capped,
            seeded_rumor_ids=[r.id for _ap, r in seeds],
            spread_rumor_ids=[r.id for r, _t in spreads],
        )

    # -- U6 deed rumors (BLM §4) -----------------------------------------------
    def _draft_seeds(
        self,
        session: GameSession,
        snapshot: WorldSnapshot,
        events: _EventApplication,
        quota: RegionQuota,
    ) -> list[tuple[DeedAppraisal, SessionRumor]]:
        """(b1) Appraisals ready to seed become rumors in the deed's region — no LLM."""
        if self._deeds is None or self._rumors is None:
            return []
        out: list[tuple[DeedAppraisal, SessionRumor]] = []
        for deed, appraisal in self._deeds.seeds_ready(session.id):
            region_id = deed.region_id
            if region_id not in snapshot.regions_by_id or quota.full(region_id):
                continue  # edited away, or full: try again next turn (BR-U6-15)
            # every stored row is in `events.distortions` (read in step (a)), so a missing
            # one has no row at all: the default (U6 review C9)
            distortion = events.distortions.get(region_id, DEFAULT_DISTORTION_DEGREE)
            out.append(
                (appraisal, self._rumors.seed(session, deed, appraisal, distortion=distortion))
            )
            quota.add(region_id)
        return out

    def _draft_spread(
        self,
        session: GameSession,
        snapshot: WorldSnapshot,
        budget: LlmBudget,
        quota: RegionQuota,
        seeds: list[tuple[DeedAppraisal, SessionRumor]],
        *,
        llm_failed: bool,
    ) -> tuple[list[tuple[SessionRumor, SpreadTarget]], bool]:
        """(b2) One hop per deed rumor version per turn (BR-U6-16..22): strongest parent
        first, at most ``max_spread_per_region_turn`` per region, one LLM call per hop.
        A failed call trips the breaker for the rest of the turn."""
        rumor_service = self._rumors
        if (
            llm_failed
            or self._deeds is None
            or rumor_service is None
            or not rumor_service.llm_available
        ):
            return [], llm_failed
        every = self._repo.list_rumors_by_origin(session.id, include_inactive=True)
        parents = sorted((r for r in every if r.active), key=lambda r: (-r.support, r.id))
        if not parents:
            return [], llm_failed
        reached: defaultdict[str, set[str]] = defaultdict(set)
        for r in every:  # one read: active parents and every region ever reached (C3)
            reached[r.origin_appraisal_id or ""].add(r.region_id)
        for appraisal, r in seeds:
            reached[appraisal.id].add(r.region_id)
        # only the parents' origin deeds, not the session's whole history (U7 review C5)
        wanted = sorted({p.origin_deed_id for p in parents if p.origin_deed_id})
        origin = {d.id: d.region_id for d in self._repo.list_deeds(session.id, deed_ids=wanted)}
        graph = passable_both_ways(snapshot)
        near = neighbour_map(graph)
        reach_from: dict[str, dict[str, float]] = {}  # memo per origin region (C4)
        per_region: Counter[str] = Counter()
        out: list[tuple[SessionRumor, SpreadTarget]] = []
        for parent in parents:
            key = parent.origin_appraisal_id
            start = origin.get(parent.origin_deed_id or "")
            if key is None or start is None:
                continue
            if start not in reach_from:
                reach_from[start] = best_path_weights(start, graph)
            for target in plan_spread(
                snapshot,
                parent,
                origin_region_id=start,
                reached=reached[key],
                tuning=self._params,
                edges=graph,
                reach=reach_from[start],
                neighbours=near,
            ):
                if per_region[target.region_id] >= self._params.max_spread_per_region_turn:
                    continue
                if quota.full(target.region_id):
                    continue
                if budget.exhausted:
                    return out, llm_failed
                budget.take(1)
                child = rumor_service.spread(session, parent, target)
                if child is None:  # circuit breaker (NFR R-02, BR-U6-22)
                    return out, True
                out.append((child, target))
                reached[key].add(target.region_id)
                per_region[target.region_id] += 1
                quota.add(target.region_id)
        return out, llm_failed

    def _store_deed_rumors(
        self,
        u,
        session: GameSession,
        snapshot: WorldSnapshot,
        seeds: list[tuple[DeedAppraisal, SessionRumor]],
        spreads: list[tuple[SessionRumor, SpreadTarget]],
    ) -> set[str]:
        """(c) Save this turn's seeds and hops with their timeline lines; return their ids
        (they skip this turn's decay)."""
        names = names_of(snapshot)
        for appraisal, rumor in seeds:
            u.rumors.upsert_rumors([rumor])
            u.deeds.mark_seeded(session.id, appraisal.id, rumor.id)
            teller: NPC | None = movement.find_npc(snapshot, appraisal.npc_id)
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.DEED_SEEDED,
                    f"deed rumor born in {region_name(names, rumor.region_id)}",
                    {
                        "deed_id": appraisal.deed_id,
                        "appraisal_id": appraisal.id,
                        "npc_name": teller.name if teller is not None else appraisal.npc_id,
                        "rumor_id": rumor.id,
                        "region_id": rumor.region_id,
                        "region_name": region_name(names, rumor.region_id),
                    },
                )
            )
        for rumor, target in spreads:
            u.rumors.upsert_rumors([rumor])
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.RUMOR_SPREAD,
                    f"rumor spread {region_name(names, target.from_region_id)} -> "
                    f"{region_name(names, target.region_id)}",
                    {
                        "deed_id": rumor.origin_deed_id,
                        "rumor_id": rumor.id,
                        "from_region_id": target.from_region_id,
                        "from_region_name": region_name(names, target.from_region_id),
                        "region_id": target.region_id,
                        "region_name": region_name(names, target.region_id),
                        "weight": round(target.weight, 4),
                        "degree": round(target.degree, 4),
                    },
                )
            )
        return {r.id for _ap, r in seeds} | {r.id for r, _t in spreads}

    # -- internals -----------------------------------------------------------
    def _compute_events(self, session: GameSession, snapshot: WorldSnapshot) -> _EventApplication:
        """Apply all ACTIVE events to region distortion **in memory** (step (a)).

        Canonical topology is read-only (NFR-P2). one_shot events auto-resolve
        (BR-P2-4); persistent ones accumulate contributions for later restore
        (BR-P2-3/5). Nothing is written here: the unit of work persists the result.
        """
        topo = snapshot.topo
        names = {r.id: r.name for r in topo.regions}
        active = self._repo.list_events(session.id, EventStatus.ACTIVE.value)
        cur = {
            rd.region_id: rd.distortion_degree
            for rd in self._repo.list_region_distortions(session.id)
        }
        out = _EventApplication()
        for ev in active:
            base = dynamics.distortion_delta(ev.magnitude, max_delta=self._params.event_max_delta)
            deltas = dynamics.propagate_delta(
                ev.region_id, base, topo.connections, min_weight=self._params.event_propagate_min
            )
            updated = dynamics.apply_deltas(cur, deltas)
            # Accumulate the *effective* (post-clamp) change, not the raw delta, so
            # resolve restores exactly what was applied even when distortion
            # saturated at 1.0 — otherwise the restore over-subtracts and drives
            # the region below its pre-event baseline.
            effective = {
                rid: updated[rid] - cur.get(rid, DEFAULT_DISTORTION_DEGREE) for rid in deltas
            }
            cur = updated
            ev.accumulate(effective)
            out.applied_ids.append(ev.id)
            out.event_regions[ev.id] = ev.region_id
            out.target_regions.add(ev.region_id)
            out.influenced_regions |= set(deltas)
            out.event_updates.append(ev)
            out.timeline.append(
                self._entry(
                    session,
                    TimelineKind.EVENT_APPLIED,
                    f"applied {ev.category} event in {region_name(names, ev.region_id)}",
                    {"event_id": ev.id, "deltas": effective, **where(names, ev.region_id)},
                )
            )
            if ev.is_one_shot():  # BR-P2-4: 1-shot, no restore
                ev.resolve(session.turn + 1)
                out.resolved_ids.append(ev.id)
                out.timeline.append(  # U7 (BR-U7-8): the automatic end is recorded too
                    self._entry(
                        session,
                        TimelineKind.EVENT_RESOLVED,
                        f"{ev.category} event in {region_name(names, ev.region_id)} ended",
                        {"event_id": ev.id, "restored": {}, **where(names, ev.region_id)},
                    )
                )
        out.distortions = cur
        return out
