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
from datetime import datetime, timezone

from pydantic import Field

from locus.knowledge.cache import SnapshotSource
from locus.play.base import SessionAppService, SessionClosedError  # noqa: F401  (re-exported)
from locus.play.errors import InvalidActionError, TurnInProgressError  # noqa: F401
from locus.play.event import dynamics
from locus.play.models import (
    DEFAULT_DISTORTION_DEGREE,
    ActionResult,
    EndTalkAction,
    EventStatus,
    GameSession,
    MoveAction,
    PlayerAction,
    SessionEvent,
    TimelineEntry,
    TimelineKind,
    TurnResult,  # noqa: F401  (re-exported: lives in models since U4)
    TurnRun,
    TurnRunStatus,
    WaitAction,
)
from locus.play.player import movement
from locus.play.ports import PlayRepository
from locus.play.rumor import dynamics as rumor_dynamics
from locus.play.rumor import promotion
from locus.play.rumor.dynamics import DEFAULT_RUMOR_DYNAMICS
from locus.play.rumor.feedback import RumorFeedbackService
from locus.play.rumor.service import SKIP_BUDGET, SKIP_CAPPED, SKIP_LLM_FAILED, RumorService
from locus.play.turn.budget import LlmBudget
from locus.play.turn.changes import shape_region_changes
from locus.play.turn.executor import SyncTurnExecutor, TurnExecutor
from locus.play.turn.guard import TurnGuard
from locus.play.turn.summary import merge_changes, narrate, scope_changes
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import LocusModel, WorldSnapshot

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
    ) -> None:
        super().__init__(repo)
        self._snapshots = snapshots
        self._rumors = rumors  # None without an LLM provider: drafts are skipped (Q6)
        self._feedback = feedback
        self._params = params
        self._guard = guard if guard is not None else TurnGuard()
        self._executor = executor if executor is not None else SyncTurnExecutor()

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
        promotion_threshold: float = promotion.DEFAULT_PROMOTION_THRESHOLD,
    ) -> ActionResult:
        """Run the action's turns synchronously (P7). ``None`` = GM manual turn (1)."""
        run = self._start(session_id, action)
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
        promotion_threshold: float = promotion.DEFAULT_PROMOTION_THRESHOLD,
    ) -> TurnRun:
        """Record the action at once and run its turns in the background (Q4=A)."""
        run = self._start(session_id, action)
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
    def _start(self, session_id: str, action: PlayerAction | None) -> TurnRun:
        """Guard + validate against the current position + immediate state (BLM §4.1)."""
        session = self._require_open(session_id)
        snapshot = self._snapshots.get(session.world_id)
        run = TurnRun(session_id=session_id, action=action, started_turn=session.turn)
        self._guard.acquire(session_id, run.id)  # TurnInProgressError -> 409
        try:
            player = self._repo.get_player(session_id)
            option = None
            if action is not None:
                if player is None:
                    raise InvalidActionError("session has no player")
                option = movement.validate_action(snapshot, player, action, self._params)
            run.cost_turns = movement.action_cost(action, option)
            with self._repo.uow() as u:
                if player is not None and action is not None:
                    if isinstance(action, MoveAction):
                        from_id, to_id = player.region_id, action.to_region_id
                        # Remembered so a failed run can put the player back: the
                        # immediate state commits in its own transaction, independent of
                        # the turn loop (code review U4-2 #5).
                        run.from_region_id = from_id
                        run.turns_charged = run.cost_turns
                        player.region_id = to_id
                        player.turns_spent += run.cost_turns
                        u.players.update_player(player)
                        names = {r.id: r.name for r in snapshot.topo.regions}
                        u.timeline.append_timeline(
                            self._entry(
                                session,
                                TimelineKind.PLAYER_MOVED,
                                f"{player.name} → {names.get(to_id, to_id)}",
                                {
                                    "player_id": player.id,
                                    "from_region_id": from_id,
                                    "from_region_name": names.get(from_id, from_id),
                                    "to_region_id": to_id,
                                    "to_region_name": names.get(to_id, to_id),
                                    "region_id": to_id,
                                    "region_name": names.get(to_id, to_id),
                                    "cost_turns": run.cost_turns,
                                },
                            )
                        )
                    elif isinstance(action, WaitAction):
                        run.turns_charged = 1
                        player.turns_spent += 1
                        u.players.update_player(player)
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
                    elif isinstance(action, EndTalkAction):  # dialogue itself is U5
                        run.turns_charged = 1
                        player.turns_spent += 1
                        u.players.update_player(player)
                run = u.runs.create_run(run)
        except BaseException:
            self._guard.release(session_id)
            raise
        return run

    def _run(self, run_id: str, session_id: str, promotion_threshold: float) -> None:
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

    def _run_turns(self, run: TurnRun, *, promotion_threshold: float) -> ActionResult:
        results: list[TurnResult] = []
        used, exhausted, failed = 0, False, False
        for _ in range(run.cost_turns):
            # Re-check OPEN at every turn boundary: `close_session`'s idle check is a
            # check, not a lock, so a session closed in the gap (or by the CLI, which
            # cannot share this process's guard) must stop the loop instead of writing
            # rumors and turns into a closed session (code review U4-2 #11).
            session = self._require_open(run.session_id)
            budget = LlmBudget(self._params.max_llm_calls_per_turn)
            tr = self._one_turn(session, budget, promotion_threshold)
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
            llm_failed=failed,
            llm_available=self.llm_available,
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
            if player is not None and run.turns_charged:
                refund = max(0, run.turns_charged - advanced)
                if refund:
                    player.turns_spent = max(0, player.turns_spent - refund)
                    if advanced == 0 and run.from_region_id is not None:
                        player.region_id = run.from_region_id  # the move never happened
                    u.players.update_player(player)
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
        self, session: GameSession, budget: LlmBudget, promotion_threshold: float
    ) -> TurnResult:
        """Compute -> draft -> store (BLM §4.3). Step order inside the store phase is
        the pre-U4 sequence: feedback → reinforce/decay → prune → promotion
        (BR-H1-12) → batch upsert → bump."""
        snapshot = self._snapshots.get(session.world_id)

        # (a) compute: ACTIVE events -> post-event distortion, in memory
        events = self._compute_events(session, snapshot)

        # (b) draft: new rumors per target region at the post-event distortion,
        #     under the turn budget and the per-region caps (LLM, outside any UoW)
        drafts: dict[str, list] = {}
        skipped: list[str] = []
        capped: list[str] = []
        llm_failed = False
        rumor_service = self._rumors
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
                distortion = events.distortions.get(region_id)
                if distortion is None:
                    distortion = self._repo.get_region_distortion(session.id, region_id)
                new, reason = rumor_service.append_for_turn(
                    session,
                    region_id,
                    distortion=distortion,
                    budget=budget,
                    max_new=self._params.max_new_rumors_per_region_turn,
                    max_active=self._params.max_active_rumors_per_region,
                    min_source_support=self._params.min_source_support,
                )
                if new:
                    drafts[region_id] = new
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
            for rid in sorted(events.influenced_regions):
                if rid in events.distortions:
                    u.distortions.set_region_distortion(session.id, rid, events.distortions[rid])
            for entry in events.timeline:
                u.timeline.append_timeline(entry)
            added_by_region: dict[str, list[str]] = {}
            for region_id, new_rumors in drafts.items():
                u.rumors.upsert_rumors(new_rumors)
                added_by_region[region_id] = [r.id for r in new_rumors]

            rumors = u.rumors.list_rumors(session.id)  # ACTIVE only (BR-H1-6/11)
            feedback_deltas = self._feedback.apply_feedback(session, rumors, store=u.distortions)
            reinforced = events.influenced_regions | set(feedback_deltas)  # BR-H1-2
            if events.influenced_regions:
                dynamics.evolve_support(rumors, events.influenced_regions)
            rumor_dynamics.decay_support(rumors, reinforced, decay=self._params.support_decay)
            survivors, prunable = rumor_dynamics.partition_prunable(
                rumors, floor=self._params.prune_floor
            )
            for r in prunable:
                r.active = False
                u.timeline.append_timeline(
                    self._entry(session, TimelineKind.PRUNE, f"pruned {r.id}", {"rumor_id": r.id})
                )
            res = promotion.evaluate(survivors, promotion_threshold)
            promoted = set(res.promoted_ids)
            demoted = set(res.demoted_ids)
            for r in survivors:
                if r.id in promoted:
                    r.promoted = True
                    u.timeline.append_timeline(
                        self._entry(
                            session, TimelineKind.PROMOTE, f"promoted {r.id}", {"rumor_id": r.id}
                        )
                    )
                elif r.id in demoted:
                    r.promoted = False
                    u.timeline.append_timeline(
                        self._entry(
                            session, TimelineKind.DEMOTE, f"demoted {r.id}", {"rumor_id": r.id}
                        )
                    )
            u.rumors.upsert_rumors(rumors)  # batch (FR-H5 / BR-H1-13)
            new_turn = u.sessions.bump_turn(session.id)
            pruned_ids = [r.id for r in prunable]
            feedback_regions = sorted(feedback_deltas)
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
        )

    # -- internals -----------------------------------------------------------
    def _compute_events(self, session: GameSession, snapshot: WorldSnapshot) -> _EventApplication:
        """Apply all ACTIVE events to region distortion **in memory** (step (a)).

        Canonical topology is read-only (NFR-P2). one_shot events auto-resolve
        (BR-P2-4); persistent ones accumulate contributions for later restore
        (BR-P2-3/5). Nothing is written here: the unit of work persists the result.
        """
        topo = snapshot.topo
        active = self._repo.list_events(session.id, EventStatus.ACTIVE.value)
        cur = {
            rd.region_id: rd.distortion_degree
            for rd in self._repo.list_region_distortions(session.id)
        }
        out = _EventApplication()
        for ev in active:
            base = dynamics.distortion_delta(ev.magnitude)
            deltas = dynamics.propagate_delta(ev.region_id, base, topo.connections)
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
            if ev.is_one_shot():  # BR-P2-4: 1-shot, no restore
                ev.resolve(session.turn + 1)
                out.resolved_ids.append(ev.id)
            out.event_updates.append(ev)
            out.timeline.append(
                self._entry(
                    session,
                    TimelineKind.EVENT_APPLIED,
                    f"applied event {ev.id}",
                    {"event_id": ev.id, "region_id": ev.region_id, "deltas": effective},
                )
            )
        out.distortions = cur
        return out
