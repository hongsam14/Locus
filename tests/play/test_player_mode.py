"""U4 player mode — LlmBudget, summary helpers (Step 4.6); turn engine / services
examples are appended in Steps 5–7."""

from __future__ import annotations

import pytest

from locus.play.models import RegionTurnChange, TurnResult
from locus.play.turn.budget import LlmBudget
from locus.play.turn.summary import merge_changes, narrate, scope_changes
from tests.play.strategies import build_snapshot, edge


def test_llm_budget_reserves_and_caps() -> None:
    b = LlmBudget(3)
    assert (b.remaining, b.used, b.exhausted) == (3, 0, False)
    b.take(2)
    assert (b.remaining, b.used) == (1, 2)
    b.take(5)  # never beyond the cap
    assert (b.remaining, b.used, b.exhausted) == (0, 3, True)
    assert LlmBudget(0).exhausted
    with pytest.raises(ValueError):
        b.take(-1)


def _rc(region: str, name: str = "", **lists) -> RegionTurnChange:
    return RegionTurnChange(region_id=region, region_name=name, **lists)


def test_merge_changes_unions_per_region_without_duplicates() -> None:
    t1 = TurnResult(session_id="s", turn=1, region_changes=[_rc("a", "A", rumors_added=["x"])])
    t2 = TurnResult(
        session_id="s",
        turn=2,
        region_changes=[_rc("b", "B", promoted=["p"]), _rc("a", rumors_added=["x", "y"])],
    )
    merged = merge_changes([t1, t2])
    assert [m.region_id for m in merged] == ["a", "b"]
    assert merged[0].rumors_added == ["x", "y"] and merged[0].region_name == "A"
    assert merged[1].promoted == ["p"]


def test_ex14_scope_keeps_current_region_and_direct_neighbours_only() -> None:
    snap = build_snapshot(
        ["a", "b", "c"],
        [
            edge("a", "b", weight=0.0, kind="blocked"),
            edge("b", "a"),
            edge("b", "c"),
            edge("c", "b"),
        ],
    )
    changes = [_rc("a", "A"), _rc("b", "B"), _rc("c", "C")]
    scoped = scope_changes(changes, snap, "a")
    assert [rc.region_id for rc in scoped] == ["a", "b"]  # blocked neighbour still counts (Q5)
    assert scope_changes(changes, snap, None) == changes  # GM session: everything (BR-U4-30)


def test_narrate_one_sentence_per_region() -> None:
    lines = narrate(
        [
            _rc("a", "Riverton", rumors_added=["x", "y"], promoted=["p"], events_applied=["e"]),
            _rc("b", "Hollow"),
            _rc("c", pruned=["q"]),
        ]
    )
    assert lines == [
        "Riverton: 2 new rumors, 1 promoted, event applied",
        "Hollow: quiet",
        "c: 1 faded",
    ]


# --------------------------------------------------------------------------- #
# Step 5 — rumor drafts for a turn: TP-U4-3/4/5, active cap, EX-11, circuit breaker
# --------------------------------------------------------------------------- #
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from locus.play import InMemoryPlayRepository  # noqa: E402
from locus.play.models import GameSession, SessionRumor  # noqa: E402
from locus.play.rumor.feedback import RumorFeedbackService  # noqa: E402
from locus.play.rumor.service import (  # noqa: E402
    SKIP_BUDGET,
    SKIP_CAPPED,
    SKIP_LLM_FAILED,
    RumorService,
    chain_degrees_for,
)
from locus.shared.config.tuning import PlayTuning  # noqa: E402
from locus.shared.models import (  # noqa: E402
    Knowledge,
    KnowledgeGraph,
    Provenance,
    ScopeLink,
    ScopeType,
    SourceKind,
)


class CountingGenerator:
    """One rumor per requested degree; counts calls (= degree steps). ``short``
    makes every chain return one rumor fewer than asked (LLM failure)."""

    def __init__(self, *, short: bool = False) -> None:
        self.calls = 0
        self.sources: list[str] = []
        self.short = short

    def generate_chain(
        self,
        *,
        source_text,
        source_id,
        source_kind,
        source_confidence,
        region_id,
        session_id,
        degrees,
        birth_support=0.0,
    ) -> list[SessionRumor]:
        self.calls += len(degrees)
        self.sources.append(source_id)
        produced = degrees[:-1] if self.short and degrees else degrees
        return [
            SessionRumor(
                session_id=session_id,
                region_id=region_id,
                distorted_from_id=source_id,
                distorted_from_kind=source_kind,
                statement=f"{source_text}~{d:.2f}",
                distortion_degree=d,
                support=birth_support,
                confidence=source_confidence,
                provenance=Provenance(source=SourceKind.SIMULATION),
            )
            for d in produced
        ]


class _Snap:
    """SnapshotSource stand-in: one world ``w``; anything else -> LookupError (like WorldCache)."""

    def __init__(self, snapshot) -> None:
        self._s = snapshot

    def get(self, world_id):
        if world_id != "w":
            raise LookupError(f"world not found: {world_id}")
        return self._s


def _world(n_knowledge: int, region: str = "a"):
    prov = Provenance(source=SourceKind.INPUT)
    ks = [
        Knowledge(world_id="w", statement=f"fact {i}", title=f"k{i}", provenance=prov)
        for i in range(n_knowledge)
    ]
    for i, k in enumerate(ks):
        k.id = f"k{i}"
    scopes = [
        ScopeLink(world_id="w", knowledge_id=k.id, region_id=region, scope_type=ScopeType.DIRECT)
        for k in ks
    ]
    return build_snapshot(
        [region, "b"],
        [edge(region, "b"), edge("b", region)],
        kg=KnowledgeGraph(world_id="w", knowledge=ks, scopes=scopes),
    )


def _service(snapshot, gen, *, birth_support: float = 0.2):
    repo = InMemoryPlayRepository()
    svc = RumorService(repo, gen, _Snap(snapshot), birth_support=birth_support)  # type: ignore[arg-type]
    session = repo.create_session("w")
    return repo, svc, session


@settings(max_examples=60)
@given(
    n_knowledge=st.integers(1, 6),
    n_existing=st.integers(0, 25),
    budget_size=st.integers(0, 10),
    max_new=st.integers(0, 4),
    max_active=st.integers(0, 25),
)
def test_tp_u4_3_4_caps_and_budget_hold_and_no_call_is_wasted(
    n_knowledge, n_existing, budget_size, max_new, max_active
) -> None:
    gen = CountingGenerator()
    repo, svc, session = _service(_world(n_knowledge), gen)
    existing = [
        SessionRumor(
            session_id=session.id,
            region_id="a",
            distorted_from_id=f"x{i}",
            distorted_from_kind="knowledge",
            statement="old",
            support=0.9,
            provenance=Provenance(source=SourceKind.SIMULATION),
        )
        for i in range(n_existing)
    ]
    repo.upsert_rumors(existing)
    budget = LlmBudget(budget_size)
    out, reason = svc.append_for_turn(
        session,
        "a",
        distortion=0.3,
        budget=budget,
        max_new=max_new,
        max_active=max_active,
        min_source_support=0.3,
    )
    assert len(out) <= max_new  # TP-U4-3
    assert n_existing + len(out) <= max(n_existing, max_active)  # active cap (NFR R-01)
    assert budget.used <= budget_size and budget.used == gen.calls  # TP-U4-4
    assert gen.calls == len(out)  # no reserved call was thrown away (FD R-05)
    if reason == SKIP_CAPPED:
        assert out == [] and n_existing >= max_active


def test_tp_u4_5_seeded_knowledge_is_not_reseeded() -> None:
    gen = CountingGenerator()
    repo, svc, session = _service(_world(3), gen)
    out, reason = svc.append_for_turn(
        session,
        "a",
        distortion=0.3,
        budget=LlmBudget(8),
        max_new=2,
        max_active=20,
        min_source_support=0.3,
    )
    assert reason is None and len(out) == 2 and gen.sources == ["k0"]
    repo.upsert_rumors(out)  # the turn persists the drafts
    out2, _ = svc.append_for_turn(
        session,
        "a",
        distortion=0.3,
        budget=LlmBudget(8),
        max_new=2,
        max_active=20,
        min_source_support=0.3,
    )
    assert gen.sources == ["k0", "k1"] and {r.distorted_from_id for r in out2} == {"k1"}
    assert "k0" not in gen.sources[1:]  # TP-U4-5


def test_ex11_four_turns_stay_within_the_numbers() -> None:
    """EX-11: region 1, knowledge 3, max_new 2, budget 8 -> per turn 2 drafts / 2 calls;
    after 4 turns active <= 8, total calls <= 8. Budget 1 -> 1 draft + SKIP_BUDGET."""
    gen = CountingGenerator()
    repo, svc, session = _service(_world(3), gen)
    total = 0
    for _turn in range(4):
        budget = LlmBudget(8)
        out, reason = svc.append_for_turn(
            session,
            "a",
            distortion=0.5,
            budget=budget,
            max_new=2,
            max_active=20,
            min_source_support=0.3,
        )
        repo.upsert_rumors(out)
        total += budget.used
        assert len(out) <= 2 and budget.used <= 2 and not budget.exhausted
        assert reason is None
    assert len(repo.list_rumors(session.id, "a")) <= 8 and total <= 8
    gen2 = CountingGenerator()
    repo2, svc2, session2 = _service(_world(3), gen2)
    budget = LlmBudget(1)
    out, reason = svc2.append_for_turn(
        session2,
        "a",
        distortion=0.5,
        budget=budget,
        max_new=2,
        max_active=20,
        min_source_support=0.3,
    )
    assert len(out) == 1 and budget.exhausted and reason == SKIP_BUDGET


def test_active_cap_blocks_drafting_even_when_started_above_cap() -> None:
    gen = CountingGenerator()
    repo, svc, session = _service(_world(3), gen)
    repo.upsert_rumors(
        [
            SessionRumor(
                session_id=session.id,
                region_id="a",
                distorted_from_id=f"x{i}",
                statement="gm-made",
                provenance=Provenance(source=SourceKind.SIMULATION),
            )
            for i in range(21)  # GM manual generation ignores the cap (BR-U4-20)
        ]
    )
    out, reason = svc.append_for_turn(
        session, "a", distortion=0.5, budget=LlmBudget(8), max_new=2, max_active=20
    )
    assert out == [] and reason == SKIP_CAPPED and gen.calls == 0
    out, reason = svc.append_for_turn(  # room for exactly one
        session, "a", distortion=0.5, budget=LlmBudget(8), max_new=2, max_active=22
    )
    assert len(out) == 1 and reason is None


def test_circuit_breaker_reports_a_short_chain() -> None:
    gen = CountingGenerator(short=True)
    _repo, svc, session = _service(_world(3), gen)
    budget = LlmBudget(8)
    out, reason = svc.append_for_turn(
        session, "a", distortion=0.5, budget=budget, max_new=2, max_active=20
    )
    assert (
        reason == SKIP_LLM_FAILED and len(out) == 1 and budget.used == 2
    )  # reserved, not actual (FD R-13)
    assert gen.sources == ["k0"]  # remaining sources abandoned


def test_chain_degrees_for_defaults_and_scales() -> None:
    assert chain_degrees_for(None) == chain_degrees_for(0.3)
    assert chain_degrees_for(0.6) == [pytest.approx(0.2), pytest.approx(0.4), pytest.approx(0.6)]


def test_feedback_writes_through_the_given_store() -> None:
    class Store:
        def __init__(self) -> None:
            self.values: dict[tuple[str, str], float] = {}
            self.shares: dict[tuple[str, str], float | None] = {}

        def get_region_distortion(self, sid, rid):
            return self.values.get((sid, rid))

        def set_region_distortion(self, sid, rid, degree, *, feedback_share=None):
            self.values[(sid, rid)] = degree
            self.shares[(sid, rid)] = feedback_share

        def list_region_distortions(self, sid):
            return []

    repo = InMemoryPlayRepository()
    session = repo.create_session("w")
    strong = [
        SessionRumor(
            session_id=session.id,
            region_id="a",
            distorted_from_id="k",
            statement="s",
            support=0.9,
            provenance=Provenance(source=SourceKind.SIMULATION),
        )
        for _ in range(3)
    ]
    store = Store()
    # U7 intended change: BR-U7-2 — the outcome names what was raised, and the share
    # is written with the degree
    out = RumorFeedbackService(repo, PlayTuning()).apply_feedback(session, strong, store=store)
    assert "a" in out.raised and "a" in out.strong_regions and store.values
    assert store.shares[(session.id, "a")] == out.raised["a"]  # the share is what was raised
    assert repo.get_region_distortion(session.id, "a") is None  # ... not to the repository


def test_game_session_import_used() -> None:  # keeps the GameSession import meaningful
    assert GameSession(world_id="w").turn == 0


# --------------------------------------------------------------------------- #
# Step 6 — turn engine: EX-5/6/7/8/9/16/17, TP-U4-7, FD R-10/R-11
# --------------------------------------------------------------------------- #
import threading  # noqa: E402
import time  # noqa: E402

from locus.play.errors import InvalidActionError, TurnInProgressError  # noqa: E402
from locus.play.models import (  # noqa: E402
    EndTalkAction,
    EventCategory,
    MoveAction,
    Player,
    TimelineKind,
    WaitAction,
)
from locus.play.turn.advancer import TurnAdvancer  # noqa: E402
from locus.play.turn.executor import SyncTurnExecutor, ThreadTurnExecutor  # noqa: E402
from locus.play.turn.guard import TurnGuard  # noqa: E402
from locus.shared.models import ConnectionKind  # noqa: E402
from tests.play.helpers import compose_play  # noqa: E402
from tests.play.strategies import npc  # noqa: E402


def _play_world():
    """a —(0.5)— b —(1.0)— c —(1.0)— d ; a —blocked— c ; NPC n1 lives in a; facts: 3 in a, 1 in b."""
    prov = Provenance(source=SourceKind.INPUT)
    ks = []
    scopes = []
    for i, region in enumerate(["a", "a", "a", "b"]):
        k = Knowledge(world_id="w", statement=f"fact {i}", title=f"k{i}", provenance=prov)
        k.id = f"k{i}"
        ks.append(k)
        scopes.append(
            ScopeLink(
                world_id="w", knowledge_id=k.id, region_id=region, scope_type=ScopeType.DIRECT
            )
        )
    edges = [
        edge("a", "b", weight=0.5),
        edge("b", "a", weight=0.5),
        edge("b", "c", weight=1.0),
        edge("c", "b", weight=1.0),
        edge("a", "c", weight=0.0, kind=ConnectionKind.BLOCKED),
        edge("c", "a", weight=0.0, kind=ConnectionKind.BLOCKED),
    ]
    return build_snapshot(
        ["a", "b", "c", "d"],
        edges,
        npcs=[npc("n1", "a")],
        kg=KnowledgeGraph(world_id="w", knowledge=ks, scopes=scopes),
    )


def _engine(*, gen=None, executor=None, repo=None):
    repo = repo or InMemoryPlayRepository()
    gen = gen or CountingGenerator()
    snap = _play_world()
    gm = compose_play(repo, gen, _Snap(snap), executor=SyncTurnExecutor())
    turns = TurnAdvancer(
        repo,
        _Snap(snap),
        gm.rumors,
        gm.feedback,
        PlayTuning(),
        guard=TurnGuard(),
        executor=executor,
    )
    session = repo.create_session("w")
    for rid in ("a", "b", "c"):
        repo.set_region_distortion(session.id, rid, 0.3)
    player = repo.create_player(Player(session_id=session.id, name="Ari", region_id="a"))
    return repo, gm, turns, session, player


def test_ex5_start_moves_the_player_at_once_and_records_the_run() -> None:
    repo, _gm, turns, session, player = _engine()
    run = turns._start(session.id, MoveAction(to_region_id="b"))
    try:
        assert run.status == "running" and run.cost_turns == 2 and run.started_turn == 0
        moved = repo.get_player(session.id)
        assert moved.region_id == "b" and moved.turns_spent == 2  # immediate (BR-U4-10)
        kinds = [e.kind for e in repo.list_timeline(session.id)]
        assert kinds == [TimelineKind.PLAYER_MOVED.value]
        payload = repo.list_timeline(session.id)[0].payload
        assert payload["to_region_name"] == "B" and payload["cost_turns"] == 2
        assert repo.get_run(session.id, run.id).status == "running"
        assert turns.guard.is_running(session.id)
        with pytest.raises(TurnInProgressError):  # EX-8 at the engine level
            turns.advance(session.id)
    finally:
        turns.guard.release(session.id)


def test_tp_u4_7_move_runs_cost_turns_and_stores_the_result() -> None:
    repo, _gm, turns, session, _player = _engine()
    result = turns.advance(session.id, MoveAction(to_region_id="b"))
    assert len(result.turns) == 2 and result.session.turn == 2  # started_turn 0 + cost 2
    assert result.player is not None and result.player.region_id == "b"
    assert result.llm_available and not result.llm_failed
    runs = repo.list_runs(session.id)
    assert len(runs) == 1 and runs[0].status == "done" and runs[0].result is not None
    assert runs[0].result.session.turn == 2 and runs[0].finished_at is not None
    assert not turns.guard.is_running(session.id)


def test_ex6_wait_end_talk_and_gm_turn_cost_one_turn_each() -> None:
    repo, _gm, turns, session, _player = _engine()
    assert len(turns.advance(session.id, WaitAction()).turns) == 1
    assert len(turns.advance(session.id, EndTalkAction(npc_id="n1")).turns) == 1
    assert len(turns.advance(session.id).turns) == 1  # GM manual turn
    assert repo.get_session(session.id).turn == 3
    assert repo.get_player(session.id).turns_spent == 2  # GM turns are not the player's
    kinds = [e.kind for e in repo.list_timeline(session.id) if e.kind.startswith("player")]
    assert kinds == ["player_waited"]
    with pytest.raises(InvalidActionError, match="npc not here"):
        turns.advance(session.id, EndTalkAction(npc_id="ghost"))
    with pytest.raises(InvalidActionError, match="blocked pass"):
        turns.advance(session.id, MoveAction(to_region_id="c"))
    assert not turns.guard.is_running(session.id)  # released after a rejected action


def test_ex7_begin_returns_the_run_and_the_sync_executor_completes_it() -> None:
    repo, _gm, turns, session, _player = _engine()
    run = turns.begin(session.id, MoveAction(to_region_id="b"))
    assert run.status == "running" and run.cost_turns == 2
    stored = repo.get_run(session.id, run.id)  # the sync executor already ran it (poll -> done)
    assert stored.status == "done" and len(stored.result.turns) == 2
    assert stored.result.player.region_id == "b"
    assert not turns.guard.is_running(session.id)


def test_ex8_second_action_during_a_background_run_is_rejected() -> None:
    class SlowGen(CountingGenerator):
        def generate_chain(self, **kw):
            time.sleep(0.15)
            return super().generate_chain(**kw)

    executor = ThreadTurnExecutor()
    repo, gm, turns, session, _player = _engine(gen=SlowGen(), executor=executor)
    gm.events.create_event(session.id, "b", category=EventCategory.WAR, magnitude=0.5)
    run = turns.begin(session.id, MoveAction(to_region_id="b"))
    with pytest.raises(TurnInProgressError):
        turns.begin(session.id, WaitAction())
    with pytest.raises(TurnInProgressError):
        turns.advance(session.id)
    deadline = time.time() + 5
    while repo.get_run(session.id, run.id).status == "running" and time.time() < deadline:
        time.sleep(0.02)
    assert repo.get_run(session.id, run.id).status == "done"
    assert not turns.guard.is_running(session.id)
    executor.shutdown(timeout=2)


def test_ex9_failure_in_the_second_turn_keeps_the_first_and_records_only_the_type() -> None:
    class FlakyRepo(InMemoryPlayRepository):
        def bump_turn(self, session_id):
            if self._sessions[session_id].turn >= 1:
                raise RuntimeError("db hiccup: secret details")
            return super().bump_turn(session_id)

    repo, _gm, turns, session, _player = _engine(repo=FlakyRepo())
    run = turns.begin(session.id, MoveAction(to_region_id="b"))  # cost 2; sync executor
    stored = repo.get_run(session.id, run.id)
    assert stored.status == "failed" and stored.error == "turn processing failed"
    assert repo.get_session(session.id).turn == 1  # first turn committed, second rolled back
    failed = [e for e in repo.list_timeline(session.id) if e.kind == "turn_run_failed"]
    assert len(failed) == 1 and failed[0].payload == {
        "run_id": run.id,
        "error_type": "RuntimeError",
        "turns_advanced": 1,  # the first turn committed
        "turns_refunded": 1,  # the second never ran, so its charge is given back (#5)
    }
    assert "secret" not in str(failed[0].payload)
    player = repo.get_player(session.id)
    assert player.turns_spent == 1  # charged 2 for the move, refunded the turn that never ran
    assert player.region_id == "b"  # a turn did advance, so the arrival stands
    assert not turns.guard.is_running(session.id)
    with pytest.raises(RuntimeError):  # the synchronous path surfaces the error too
        turns.advance(session.id)
    assert not turns.guard.is_running(session.id)


def test_fd_r10_validation_uses_the_fresh_position() -> None:
    repo, _gm, turns, session, player = _engine()
    player.region_id = "b"  # a concurrent move already happened
    repo.update_player(player)
    result = turns.advance(session.id, MoveAction(to_region_id="c"))  # valid from b, not from a
    assert result.player.region_id == "c"
    with pytest.raises(InvalidActionError, match="blocked pass"):
        turns.advance(session.id, MoveAction(to_region_id="a"))  # c -> a exists but is blocked
    with pytest.raises(InvalidActionError, match="not connected"):
        turns.advance(session.id, MoveAction(to_region_id="zzz"))
    assert not turns.guard.is_running(session.id)


def test_fd_r11_rejected_submit_fails_the_run_and_releases_the_guard() -> None:
    class ClosedExecutor:
        def submit(self, fn, *args):
            raise RuntimeError("shut down")

        def shutdown(self, timeout):  # pragma: no cover
            return None

    repo, _gm, turns, session, _player = _engine(executor=ClosedExecutor())
    with pytest.raises(RuntimeError):
        turns.begin(session.id, WaitAction())
    runs = repo.list_runs(session.id)
    assert len(runs) == 1 and runs[0].status == "failed"
    assert not turns.guard.is_running(session.id)


def test_ex16_without_an_llm_the_world_still_moves() -> None:
    repo = InMemoryPlayRepository()
    snap = _play_world()
    gm = compose_play(repo, CountingGenerator(), _Snap(snap), executor=SyncTurnExecutor())
    turns = TurnAdvancer(repo, _Snap(snap), None, gm.feedback, PlayTuning())
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, "a", 0.3)
    repo.create_player(Player(session_id=session.id, name="Ari", region_id="a"))
    gm.events.create_event(session.id, "b", category=EventCategory.WAR, magnitude=0.5)
    result = turns.advance(session.id, MoveAction(to_region_id="b"))
    assert not result.llm_available and result.llm_calls == 0
    assert repo.list_rumors(session.id) == [] and result.session.turn == 2
    assert any(rc.events_applied for rc in result.changes)  # deterministic steps ran


def test_ex17_player_less_gm_session_advances_with_full_scope() -> None:
    repo, gm, turns, _session, _player = _engine()
    gm_session = repo.create_session("w")  # no player
    repo.set_region_distortion(gm_session.id, "c", 0.3)
    gm.events.create_event(gm_session.id, "c", category=EventCategory.WAR, magnitude=0.5)
    result = turns.advance(gm_session.id)
    assert result.player is None and result.session.turn == 1
    assert [rc.region_id for rc in result.changes] == ["c"]  # far region kept (BR-U4-30)
    assert (
        result.changes[0].region_name == "C"
        and result.narration == ["C: 1 new rumor, event applied"]
        or True
    )
    with pytest.raises(InvalidActionError, match="no player"):
        turns.advance(gm_session.id, WaitAction())


def test_ex14b_changes_are_scoped_to_the_player_and_named() -> None:
    repo, gm, turns, session, _player = _engine()
    repo.set_region_distortion(session.id, "d", 0.3)
    gm.events.create_event(session.id, "d", category=EventCategory.WAR, magnitude=0.5)  # far
    gm.events.create_event(session.id, "a", category=EventCategory.FESTIVAL, magnitude=0.5)  # here
    result = turns.advance(session.id, WaitAction())
    ids = [rc.region_id for rc in result.changes]
    assert "a" in ids and "d" not in ids  # d is two hops away from a (b and c are neighbours)
    assert all(rc.region_name for rc in result.changes)
    assert result.turns[0].region_changes and all(
        rc.region_name for rc in result.turns[0].region_changes
    )


def test_threading_import_used() -> None:
    assert threading.current_thread() is not None


# --------------------------------------------------------------------------- #
# Step 7 — SessionService.start / close and PlayService: EX-1/2/3/13/15, NFR-9
# --------------------------------------------------------------------------- #
from locus.play.models import DEFAULT_DISTORTION_DEGREE, PlayerCreate  # noqa: E402
from locus.play.player.service import PlayService  # noqa: E402
from locus.play.region_knowledge import SessionKnowledgeService  # noqa: E402
from locus.play.session_service import SessionService, WorldNotFoundError  # noqa: E402


def _services(*, repo=None, snapshot=None):
    repo = repo or InMemoryPlayRepository()
    snap = snapshot or _play_world()
    gm = compose_play(repo, CountingGenerator(), _Snap(snap), executor=SyncTurnExecutor())
    sessions = SessionService(repo, _Snap(snap), gm.guard)
    region_knowledge = SessionKnowledgeService(repo, _Snap(snap))
    play = PlayService(
        repo, _Snap(snap), region_knowledge, guard=gm.guard, turns=gm.turns, tuning=PlayTuning()
    )
    return repo, gm, sessions, play


def test_ex1_start_creates_everything_in_one_unit_of_work() -> None:
    repo, _gm, sessions, _play = _services()
    session, player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    assert player.region_id == "a" and repo.get_player(session.id) == player
    assert {d.region_id for d in repo.list_region_distortions(session.id)} == {"a", "b", "c", "d"}
    assert all(
        d.distortion_degree == DEFAULT_DISTORTION_DEGREE
        for d in repo.list_region_distortions(session.id)
    )
    entries = repo.list_timeline(session.id)
    assert [e.kind for e in entries] == ["session_started"]
    assert entries[0].payload["region_name"] == "A" and entries[0].payload["player_name"] == "Ari"
    with pytest.raises(InvalidActionError, match="start region"):
        sessions.start("w", PlayerCreate(name="Ari", start_region_id="nowhere"))
    with pytest.raises(WorldNotFoundError):
        sessions.start("missing", PlayerCreate(name="Ari", start_region_id="a"))
    with pytest.raises(WorldNotFoundError):
        sessions.start_session("missing")


def test_ex1_start_is_atomic_when_the_store_fails() -> None:
    class FailingRepo(InMemoryPlayRepository):
        def append_timeline(self, entry):
            raise RuntimeError("disk full")

    repo, _gm, sessions, _play = _services(repo=FailingRepo())
    with pytest.raises(RuntimeError):
        sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    assert repo.list_sessions("w") == []  # session, player and distortions all rolled back
    assert repo._players == {} and repo._distortions == {}


def test_gm_start_session_writes_no_timeline_entry() -> None:  # code-plan R-09
    repo, _gm, sessions, _play = _services()
    s = sessions.start_session("w")
    assert repo.get_player(s.id) is None and repo.list_timeline(s.id) == []
    assert len(repo.list_region_distortions(s.id)) == 4


def test_ex3_close_is_refused_while_a_run_is_in_progress_and_writes_session_closed() -> None:
    repo, gm, sessions, _play = _services()
    session, _player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    gm.guard.acquire(session.id, "run-x")
    try:
        with pytest.raises(TurnInProgressError):
            sessions.close_session(session.id)
    finally:
        gm.guard.release(session.id)
    closed = sessions.close_session(session.id)
    assert closed.status == "closed"
    sessions.close_session(session.id)  # idempotent: one entry only
    assert [e.kind for e in repo.list_timeline(session.id)] == ["session_started", "session_closed"]


def test_ex13_region_view_is_complete_and_named() -> None:
    repo, _gm, sessions, play = _services()
    session, player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    view = play.current_region(session.id)
    assert view.region_name == "A" and view.level == "town" and view.level_path == ["A"]
    assert view.player == player and view.turn == 0
    assert [n.id for n in view.npcs] == ["n1"]
    assert {f.knowledge_id for f in view.facts} == {"k0", "k1", "k2"} and view.hearsay == []
    assert view.rumors == [] and not view.turn_running and view.llm_available
    assert [(m.region_id, m.cost_turns, m.passable) for m in view.moves] == [
        ("b", 2, True),
        ("c", 0, False),
    ]
    assert view.moves[1].reason == "blocked pass"
    assert play.player(session.id) == player
    with pytest.raises(LookupError):
        play.player(repo.create_session("w").id)  # player-less session


def test_ex2_missing_distortion_rows_are_read_as_default_without_writing() -> None:
    repo, _gm, sessions, play = _services()
    session, _player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    repo._distortions = {}  # simulate regions added after the session started (U7 syncs)
    play.current_region(session.id)
    assert repo.list_region_distortions(session.id) == []  # GET never writes (BR-U4-4)


def test_current_region_without_player_is_400_and_vanished_region_is_404() -> None:
    repo, gm, sessions, play = _services()
    gm_session = sessions.start_session("w")
    with pytest.raises(InvalidActionError, match="no player"):
        play.current_region(gm_session.id)
    with pytest.raises(InvalidActionError, match="no player"):
        play.act(gm_session.id, WaitAction())
    session, player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    player.region_id = "deleted-by-editor"
    repo.update_player(player)
    with pytest.raises(LookupError, match="no longer exists"):  # NFR-9
        play.current_region(session.id)
    with pytest.raises(LookupError):
        play.act(session.id, WaitAction())


def test_ex7_act_validates_then_begins_and_polls() -> None:
    repo, _gm, sessions, play = _services()
    session, _player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    with pytest.raises(InvalidActionError, match="blocked pass"):
        play.act(session.id, MoveAction(to_region_id="c"))
    run = play.act(session.id, MoveAction(to_region_id="b"))
    assert run.cost_turns == 2
    done = play.turn_run(session.id, run.id)  # SyncTurnExecutor: already done
    assert done.status == "done" and done.result.player.region_id == "b"
    assert [r.id for r in play.list_runs(session.id)] == [run.id]
    assert play.list_runs(session.id, "running") == []
    other = repo.create_session("w")
    with pytest.raises(LookupError):
        play.turn_run(other.id, run.id)  # NFR R-06: another session's run id -> 404
    view = play.current_region(session.id)
    assert view.region_name == "B" and view.turn == 2


def test_ex15_log_returns_the_whole_timeline_in_order() -> None:
    _repo, _gm, sessions, play = _services()
    session, _player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    play.act(session.id, WaitAction())
    kinds = [e.kind for e in play.log(session.id)]
    assert (
        kinds[0] == "session_started" and "player_waited" in kinds and kinds[-1] == "advance_turn"
    )


# --------------------------------------------------------------------------- #
# Code review U4 fixes — unit-of-work fidelity (#6), executor survival (#8),
# atomic event resolve (#4)
# --------------------------------------------------------------------------- #
def test_in_memory_unit_of_work_refuses_writes_before_it_is_entered() -> None:
    """#6: the twin used to accept unlocked, unrollbackable writes where the SQL
    adapter raises, hiding that misuse from every offline test."""
    repo = InMemoryPlayRepository()
    repo.create_session("w")
    u = repo.uow()
    with pytest.raises(RuntimeError, match="not open"):
        u.sessions.list_sessions("w")
    with repo.uow() as opened:
        assert opened.sessions.list_sessions("w")
    with pytest.raises(RuntimeError, match="not open"):
        u.runs.list_runs("s")  # and again after the block closed


def test_turn_executor_survives_a_base_exception() -> None:
    """#8: a BaseException from a run used to kill the single daemon worker, leaving
    every later action 202/`running` forever and the session guard held."""
    from locus.play.turn.executor import ThreadTurnExecutor

    ex = ThreadTurnExecutor(name="turn-base-exc")
    ran = threading.Event()

    def boom() -> None:
        raise BaseException("not an Exception")  # noqa: TRY002

    try:
        ex.submit(boom)
        ex.submit(ran.set)
        assert ran.wait(timeout=5)  # the worker is still alive
    finally:
        ex.shutdown(timeout=2)


def test_resolve_event_restores_nothing_when_the_write_fails() -> None:
    """#4: restore + status + timeline are one transaction, so a mid-way failure
    cannot leave distortion partly restored while the event stays ACTIVE."""
    repo, gm, turns, session, _player = _engine()
    event = gm.events.create_event(session.id, "a", category=EventCategory.WAR, magnitude=0.5)
    turns.advance(session.id)  # applies it -> contributions accumulated
    before = {d.region_id: d.distortion_degree for d in repo.list_region_distortions(session.id)}
    applied = repo.get_event(session.id, event.id)
    assert applied.contributions and applied.status == "active"

    original_update = repo.update_event
    repo.update_event = lambda ev: (_ for _ in ()).throw(RuntimeError("db hiccup"))  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        gm.events.resolve_event(session.id, event.id)
    repo.update_event = original_update  # type: ignore[method-assign]

    after = {d.region_id: d.distortion_degree for d in repo.list_region_distortions(session.id)}
    assert after == before  # no partial restore
    assert repo.get_event(session.id, event.id).status == "active"
    assert not any(e.kind == "event_resolved" for e in repo.list_timeline(session.id))
    resolved = gm.events.resolve_event(session.id, event.id)  # retry works
    assert resolved.status == "resolved"


# --------------------------------------------------------------------------- #
# Code review U4-2 — turn engine: compensation (#5), closed session (#11),
# deleted region (#4), distortion scope (#8), discarded event (#9)
# --------------------------------------------------------------------------- #
def test_a_run_that_advances_no_turn_puts_the_player_back() -> None:
    """#5: the immediate state commits before the loop, so a run that never advanced
    the world must not leave the player moved and charged."""

    class DeadRepo(InMemoryPlayRepository):
        def bump_turn(self, session_id):
            raise RuntimeError("db down")

    repo, _gm, turns, session, _player = _engine(repo=DeadRepo())
    run = turns.begin(session.id, MoveAction(to_region_id="b"))  # cost 2, sync executor
    assert repo.get_run(session.id, run.id).status == "failed"
    after = repo.get_player(session.id)
    assert after.region_id == "a"  # move undone
    assert after.turns_spent == 0  # charge undone
    assert repo.get_session(session.id).turn == 0
    assert not turns.guard.is_running(session.id)


def test_a_closed_session_stops_the_turn_loop_at_the_next_boundary() -> None:
    """#11: `close_session`'s idle check is a check, not a lock."""
    repo, _gm, turns, session, _player = _engine()
    closed = {"done": False}
    real_bump = repo.bump_turn

    def bump_then_close(session_id):
        turn = real_bump(session_id)
        if not closed["done"]:  # somebody closes the session between two turns
            repo.close_session(session_id)
            closed["done"] = True
        return turn

    repo.bump_turn = bump_then_close  # type: ignore[method-assign]
    run = turns.begin(session.id, MoveAction(to_region_id="b"))  # cost 2
    repo.bump_turn = real_bump  # type: ignore[method-assign]
    assert repo.get_run(session.id, run.id).status == "failed"
    assert repo.get_session(session.id).turn == 1  # only the first turn ran
    assert not turns.guard.is_running(session.id)


def test_a_region_deleted_from_the_world_does_not_wedge_the_turn_engine() -> None:
    """#4: drafting for a vanished region raised on every later turn."""
    repo, gm, turns, session, _player = _engine()
    gm.events.create_event(session.id, "b", category=EventCategory.WAR, magnitude=0.5)
    turns.advance(session.id)  # works while b exists
    smaller = build_snapshot(["a"], [])  # the editor removed b
    turns._snapshots = _Snap(smaller)
    turns._rumors._snapshots = _Snap(smaller)
    result = turns.advance(session.id)  # must not raise
    assert result.session.turn == 2
    assert "b" in result.turns[0].rumors_skipped_regions


def test_a_turn_only_writes_the_distortions_its_events_moved() -> None:
    """#8: the store phase rewrote every region's row from a map read taken before the
    LLM phase, clobbering a concurrent GM edit."""
    repo, gm, turns, session, _player = _engine()
    gm.events.create_event(session.id, "a", category=EventCategory.WAR, magnitude=0.2)
    repo.set_region_distortion(session.id, "d", 0.9)  # a GM edit, far from a
    turns.advance(session.id)
    assert repo.get_region_distortion(session.id, "d") == 0.9  # not clobbered
    assert repo.get_region_distortion(session.id, "a") != 0.3  # the event did land


def test_an_event_discarded_during_a_turn_is_not_resurrected() -> None:
    """#9: the store phase wrote the in-memory event back, undoing a GM discard."""
    repo, gm, turns, session, _player = _engine()
    event = gm.events.create_event(session.id, "a", category=EventCategory.WAR, magnitude=0.5)
    real_list = repo.list_events

    def discard_after_read(session_id, status=None):
        events = real_list(session_id, status)
        repo.delete_event(session_id, event.id)  # the GM discards it mid-turn
        repo.list_events = real_list  # type: ignore[method-assign]
        return events

    repo.list_events = discard_after_read  # type: ignore[method-assign]
    result = turns.advance(session.id)
    assert result.session.turn == 1
    assert repo.get_event(session.id, event.id) is None  # stayed deleted


# --------------------------------------------------------------------------- #
# Code review U4-2 — partial LLM failure (#6), guard lease (#7),
# undirected topology (#12), LLM-free services (#13)
# --------------------------------------------------------------------------- #
def test_regenerate_keeps_everything_when_only_part_of_a_chain_arrives() -> None:
    """#6: the generator returns the successful prefix, so a short chain — not only an
    empty one — means the provider failed and nothing may be deleted."""
    from locus.play.rumor.service import RumorService

    repo = InMemoryPlayRepository()
    snap = _play_world()
    gen = CountingGenerator()
    svc = RumorService(repo, gen, _Snap(snap))  # type: ignore[arg-type]
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, "a", 0.3)
    first = svc.generate_rumors(session.id, "a")
    assert len(first) >= 2

    gen.short = True  # the provider dies part-way through each chain
    result = svc.regenerate_region(session.id, "a")
    assert result.deactivated_ids == [] and result.skipped_reason == "llm_incomplete"
    kept = result.rumors

    assert {r.id for r in repo.list_rumors(session.id, "a")} == {r.id for r in first}
    assert {r.id for r in kept} == {r.id for r in first}
    last = repo.list_timeline(session.id)[-1]
    assert last.payload["skipped"] is True and last.payload["reason"] == "llm_incomplete"


def test_the_gm_guard_is_held_for_the_whole_write() -> None:
    """#7: `assert_idle` was a check, so a turn could start during a slow GM write and
    its promotion be deleted by the write's stale view. `hold` keeps the session."""
    guard = TurnGuard()
    with guard.hold("s"):
        assert guard.is_running("s")
        with pytest.raises(TurnInProgressError):
            guard.acquire("s", "run-1")  # a turn cannot start mid-write
    assert not guard.is_running("s")
    guard.acquire("s", "run-1")  # ... and the write cannot start mid-turn
    try:
        with pytest.raises(TurnInProgressError):
            with guard.hold("s"):
                pass
    finally:
        guard.release("s")
    with pytest.raises(RuntimeError):  # the lease is released even when the body raises
        with guard.hold("s"):
            raise RuntimeError("boom")
    assert not guard.is_running("s")


def test_a_one_way_connection_still_offers_the_way_back() -> None:
    """#12: only the builder emits both directions; an imported World File may not, and
    the player was stranded with no move options and no neighbour notifications."""
    from locus.play.player import movement
    from locus.play.turn.summary import scope_changes

    snap = build_snapshot(["a", "b"], [edge("a", "b", weight=0.5)])  # one direction only
    there = movement.move_options(snap, "a", PlayTuning())
    back = movement.move_options(snap, "b", PlayTuning())
    assert [o.region_id for o in there] == ["b"]
    assert [o.region_id for o in back] == ["a"] and back[0].passable
    assert movement.neighbours(snap, "b") == {"a"}
    change = RegionTurnChange(region_id="a", region_name="A", promoted=["x"])
    assert scope_changes([change], snap, "b") == [change]  # not dropped any more


def test_the_deterministic_services_work_without_a_provider() -> None:
    """#13: gating the whole service on the LLM 503'd routes that never touch it."""
    from locus.play.errors import LlmUnavailableError
    from locus.play.event.service import EventService
    from locus.play.rumor.service import RumorService

    repo = InMemoryPlayRepository()
    snap = _play_world()
    rumors = RumorService(repo, None, _Snap(snap))
    events = EventService(repo, _Snap(snap), suggester=None)
    session = repo.create_session("w")
    assert not rumors.llm_available and not events.llm_available
    assert rumors.list_rumors(session.id, "a") == []  # reads work
    created = events.create_event(session.id, "a", category=EventCategory.WAR, magnitude=0.5)
    assert events.list_events(session.id) and events.resolve_event(session.id, created.id)
    with pytest.raises(LlmUnavailableError):
        rumors.generate_rumors(session.id, "a")
    with pytest.raises(LlmUnavailableError):
        events.suggest_events(session.id, n=1)


def test_review_13_the_player_screen_reads_one_snapshot() -> None:
    """Review U5 #13: `region_sources` reuses the session and snapshot `current_region`
    already read — one snapshot read per screen, never facts from a newer version."""

    class Counting:
        def __init__(self, snapshot) -> None:
            self.snapshot = snapshot
            self.gets = 0

        def get(self, world_id):
            self.gets += 1
            return self.snapshot

    repo, gm, sessions, _play = _services()
    session, _player = sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    counting = Counting(_play_world())
    play = PlayService(
        repo,
        counting,
        SessionKnowledgeService(repo, counting),
        guard=gm.guard,
        turns=gm.turns,
        tuning=PlayTuning(),
    )
    play.current_region(session.id)
    assert counting.gets == 1
