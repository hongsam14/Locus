"""U6 deeds in the turn engine (Step 6.8): EX-1/2/6/8/9/10/11/13/18/19, TP-U6-4/6,
code-plan carries R-01 (prep failure trips the breaker) and R-04 (budget 0/1), the
NFR-3 structural assertions, and RumorService's seed / spread / reserved units."""

from __future__ import annotations

import pytest

from locus.play import InMemoryPlayRepository
from locus.play.errors import InvalidActionError
from locus.play.event.suggester import EventDraftList, EventSuggester
from locus.play.models import (
    AppraisalDraft,
    AppraisalDraftItem,
    DeclareAction,
    DeedKind,
    EndTalkAction,
    EventCategory,
    MoveAction,
    NarrationDraft,
    PlayerCreate,
    SpreadTarget,
    WaitAction,
)
from locus.play.rumor.generator import RumorDraft, RumorGenerator
from locus.play.turn.budget import LlmBudget
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import ConnectionKind
from tests.play.helpers import compose_play
from tests.play.strategies import build_snapshot, deed_rumor, edge, npc
from tests.shared.snapshots import StaticSnapshots

WORLD = build_snapshot(
    ["a", "b", "c"],
    [
        edge("a", "b", weight=0.6),
        edge("a", "c", weight=0.9, kind=ConnectionKind.BLOCKED),
        edge("b", "c", weight=0.5),
    ],
    npcs=[
        npc("n1", "a", name="Mara"),
        npc("n3", "a", name="Tom"),
        npc("n2", "b", name="Bo"),
        npc("n4", "c", name="Cid"),
    ],
)


class _Watch:
    """Shared by the fakes: records the open unit-of-work depth at every LLM call."""

    def __init__(self) -> None:
        self.repo: InMemoryPlayRepository | None = None
        self.depths: list[int] = []

    def mark(self) -> None:
        self.depths.append(self.repo.uow_depth if self.repo is not None else 0)


class VoiceLLM:
    """NPC dialogue (complete), appraisal and narration (structured)."""

    def __init__(self, watch: _Watch) -> None:
        self.watch = watch
        self.appraisal = AppraisalDraft()
        self.narration = NarrationDraft(narration="광장이 술렁인다.", record="Ari caught a thief.")
        self.fail_structured = False
        self.structured_calls: list[type] = []

    def complete(self, prompt, *, system=None):
        self.watch.mark()
        return "Hm."

    def structured(self, prompt, schema, *, system=None):
        self.watch.mark()
        self.structured_calls.append(schema)
        if self.fail_structured:
            raise RuntimeError("provider down")
        return self.appraisal if schema is AppraisalDraft else self.narration


class RumorLLM:
    def __init__(self, watch: _Watch) -> None:
        self.watch = watch
        self.calls = 0
        self.fail = False
        self.sources: list[str] = []

    def structured(self, prompt, schema, *, system=None):
        self.watch.mark()
        self.calls += 1
        self.sources.append(prompt)
        if self.fail:
            raise RuntimeError("provider down")
        return RumorDraft(statement=f"twisted #{self.calls}")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


def _setup(tuning: PlayTuning | None = None, *, voice: bool = True):
    repo = InMemoryPlayRepository()
    watch = _Watch()
    watch.repo = repo
    voice_llm = VoiceLLM(watch) if voice else None
    rumor_llm = RumorLLM(watch)
    gm = compose_play(
        repo,
        RumorGenerator(rumor_llm),
        StaticSnapshots(WORLD),
        dialogue_llm=voice_llm,
        tuning=tuning or PlayTuning(),
    )
    session, player = gm.sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    return repo, gm, session, player, voice_llm, rumor_llm, watch


def _tell(gm, voice_llm, session, *, salience=1.0, line="I caught a thief!"):
    """Declare in A, talk to Mara, end the talk with Mara judging the declaration."""
    result = gm.turns.advance(session.id, DeclareAction(text="도둑을 잡는다"), lang="ko")
    gm.dialogue.say(session.id, "n1", line)
    voice_llm.appraisal = AppraisalDraft(
        summary="Ari says Ari caught a thief.",
        appraisals=[
            AppraisalDraftItem(
                ref="d2",
                noteworthy=True,
                salience=salience,
                slant="admiring",
                retelling="The traveler caught a thief in the square!",
            )
        ],
    )
    end = gm.turns.advance(session.id, EndTalkAction(npc_id="n1"))
    return result, end


# --- EX-1: arrivals ------------------------------------------------------------------ #
def test_ex1_the_start_and_every_move_leave_an_arrival_deed() -> None:
    repo, gm, session, player, *_ = _setup()
    (start,) = repo.list_deeds(session.id)
    assert (start.kind, start.region_id, start.witnessed_npc_ids) == ("arrival", "a", ["n1", "n3"])
    started = next(e for e in repo.list_timeline(session.id) if e.kind == "session_started")
    assert started.payload["deed_id"] == start.id
    gm.turns.advance(session.id, MoveAction(to_region_id="b"))
    moved = [d for d in repo.list_deeds(session.id) if d.region_id == "b"]
    assert len(moved) == 1 and moved[0].run_id is not None
    entry = next(e for e in repo.list_timeline(session.id) if e.kind == "player_moved")
    assert entry.payload["deed_id"] == moved[0].id


# --- EX-2: declarations -------------------------------------------------------------- #
def test_ex2_a_declaration_is_narrated_once_recorded_and_costs_one_turn() -> None:
    repo, gm, session, _p, voice, _r, _w = _setup()
    result = gm.turns.advance(session.id, DeclareAction(text="  도둑을 잡는다  "), lang="ko")
    assert result.declaration.text == "광장이 술렁인다." and result.declaration.lang == "ko"
    assert voice.structured_calls == [NarrationDraft]  # exactly one narration call
    declared = [d for d in repo.list_deeds(session.id) if d.kind == "declared_action"]
    assert len(declared) == 1 and declared[0].text == "Ari caught a thief."
    assert declared[0].declaration == "도둑을 잡는다"
    assert repo.get_session(session.id).turn == 1
    assert any(e.kind == "action_declared" for e in repo.list_timeline(session.id))


@pytest.mark.parametrize("text", ["", "   ", "x" * 301])
def test_ex2_an_empty_or_too_long_declaration_is_400(text) -> None:
    _repo, gm, session, *_ = _setup()
    with pytest.raises(InvalidActionError):
        gm.turns.advance(session.id, DeclareAction(text=text))


def test_ex2_without_an_llm_a_declaration_is_still_accepted() -> None:
    repo, gm, session, *_ = _setup(voice=False)
    result = gm.turns.advance(session.id, DeclareAction(text="sing a song"), lang="en")
    assert result.declaration.llm_calls == 0 and result.declaration.lang == "en"
    (declared,) = [d for d in repo.list_deeds(session.id) if d.kind == "declared_action"]
    assert declared.text == "Ari declared: sing a song"


# --- EX-6 (US-6.5): A, then B, never C straight over the blocked pass ---------------- #
def test_ex6_my_deed_travels_a_then_b_then_c_more_distorted_each_hop() -> None:
    repo, gm, session, _p, voice, rumor_llm, _w = _setup()
    _tell(gm, voice, session)
    (seed,) = repo.list_rumors_by_origin(session.id)
    assert (seed.region_id, seed.statement) == ("a", "The traveler caught a thief in the square!")
    assert seed.support == pytest.approx(0.4)
    gm.turns.advance(session.id, WaitAction())
    at_b = [r for r in repo.list_rumors_by_origin(session.id) if r.region_id == "b"]
    assert len(at_b) == 1 and at_b[0].spread_from_region_id == "a"
    assert at_b[0].distortion_degree >= 0.4 - 1e-9 and at_b[0].support == pytest.approx(0.32)
    assert not [r for r in repo.list_rumors_by_origin(session.id) if r.region_id == "c"]
    gm.turns.advance(session.id, WaitAction())
    at_c = [r for r in repo.list_rumors_by_origin(session.id) if r.region_id == "c"]
    assert len(at_c) == 1 and at_c[0].spread_from_region_id == "b"
    assert at_c[0].distortion_degree >= 0.7 - 1e-9
    # Bo in B hears it as a rumor of his own region
    src = gm.region_knowledge.region_sources(session.id, "b")
    assert at_b[0].id in {r.id for r in src.rumors}


def test_tp_u6_6_and_nfr3_no_turn_overspends_and_no_llm_call_runs_inside_a_transaction():
    repo, gm, session, _p, voice, _r, watch = _setup(PlayTuning(max_llm_calls_per_turn=3))
    _decl, end = _tell(gm, voice, session)
    for _ in range(3):
        gm.turns.advance(session.id, WaitAction())
    for e in repo.list_timeline(session.id):
        if e.kind == "advance_turn":
            assert e.payload["llm_calls"] <= 3
    assert watch.depths and all(depth == 0 for depth in watch.depths)
    assert voice.structured_calls.count(AppraisalDraft) == 1  # one talk, one judgement


def test_nfr3_the_prep_step_writes_in_one_unit_of_work() -> None:
    repo, gm, session, *_ = _setup()
    real_prepare = gm.turns._prepare
    entered = {"n": 0}
    real_uow = repo.uow

    def counting_uow():
        entered["n"] += 1
        return real_uow()

    def watched(run, sess, budget):
        repo.uow = counting_uow  # type: ignore[method-assign]
        try:
            return real_prepare(run, sess, budget)
        finally:
            repo.uow = real_uow  # type: ignore[method-assign]

    gm.turns._prepare = watched  # type: ignore[method-assign]
    gm.turns.advance(session.id, DeclareAction(text="sing"))
    assert entered["n"] == 1


# --- EX-8 / EX-9 / R-01 / R-04: the budget order and the breaker --------------------- #
def test_ex8_spread_spends_the_budget_before_canonical_drafts() -> None:
    repo, gm, session, _p, voice, rumor_llm, _w = _setup(PlayTuning(max_llm_calls_per_turn=1))
    _tell(gm, voice, session)
    gm.events.create_event(session.id, "c", category=EventCategory.FESTIVAL, magnitude=0.8)
    before = rumor_llm.calls
    result = gm.turns.advance(session.id, WaitAction()).turns[-1]
    assert rumor_llm.calls - before == 1 and result.spread_rumor_ids  # the hop to B
    assert "c" in result.rumors_skipped_regions  # the canonical draft waited


def test_ex9_a_failed_hop_stops_the_turns_other_llm_work() -> None:
    repo, gm, session, _p, voice, rumor_llm, _w = _setup()
    _tell(gm, voice, session)
    gm.events.create_event(session.id, "c", category=EventCategory.FESTIVAL, magnitude=0.8)
    rumor_llm.fail = True
    before = rumor_llm.calls
    result = gm.turns.advance(session.id, WaitAction()).turns[-1]
    assert result.llm_failed and rumor_llm.calls - before == 1  # no canonical attempt after


def test_review_r01_a_failed_prep_call_trips_the_breaker_for_its_turn() -> None:
    repo, gm, session, _p, voice, rumor_llm, _w = _setup()
    _tell(gm, voice, session)  # a deed rumor in A, ready to spread
    gm.dialogue.say(session.id, "n3", "Hello Tom.")
    voice.fail_structured = True
    before = rumor_llm.calls
    result = gm.turns.advance(session.id, EndTalkAction(npc_id="n3"))
    assert result.llm_failed and rumor_llm.calls == before  # no hop this turn


def test_review_r04_budget_zero_falls_back_and_budget_one_only_narrates() -> None:
    _repo, gm, session, _p, voice, rumor_llm, _w = _setup(PlayTuning(max_llm_calls_per_turn=0))
    result = gm.turns.advance(session.id, DeclareAction(text="sing"))
    assert result.declaration.llm_calls == 0 and voice.structured_calls == []
    repo, gm, session, _p, voice, rumor_llm, _w = _setup(PlayTuning(max_llm_calls_per_turn=1))
    _tell(gm, voice, session)
    before = rumor_llm.calls
    gm.turns.advance(session.id, DeclareAction(text="dance"))  # its turn: narration only
    assert rumor_llm.calls == before


# --- EX-10 / TP-U6-4: a void reaches everything, now and later ----------------------- #
def test_ex10_tp_u6_4_after_a_void_nothing_of_the_deed_comes_back() -> None:
    repo, gm, session, _p, voice, _r, _w = _setup()
    _tell(gm, voice, session)
    gm.turns.advance(session.id, WaitAction())
    deed_id = repo.list_rumors_by_origin(session.id)[0].origin_deed_id
    result = gm.deeds.void(session.id, deed_id)
    assert result.deactivated_rumor_ids
    for _ in range(3):
        gm.turns.advance(session.id, WaitAction())
    assert repo.list_rumors_by_origin(session.id, deed_id=deed_id) == []
    lineage = {
        r.id
        for r in repo.list_rumors(session.id, include_pruned=True)
        if r.origin_deed_id == deed_id
    }
    assert all(
        not r.active for r in repo.list_rumors(session.id, include_pruned=True) if r.id in lineage
    )


# --- EX-11 / EX-18: regenerate keeps deed rumors; canonical chains never use them ------ #
def test_ex11_regenerate_keeps_the_deed_rumor_and_ex18_never_seeds_from_it() -> None:
    repo, gm, session, _p, voice, rumor_llm, _w = _setup()
    _tell(gm, voice, session)
    (seed,) = repo.list_rumors_by_origin(session.id)
    seed.support = 0.9  # well above the canonical re-seed threshold
    repo.upsert_rumors([seed])
    result = gm.rumors.regenerate_region(session.id, "a")
    assert seed.id in {r.id for r in result.kept} and seed.id not in result.deactivated_ids
    # EX-18: the paths that do extend existing rumors — GM generate and the turn's
    # canonical drafts — never take a deed rumor as a chain source (BR-U6-35)
    rumor_llm.sources.clear()
    gm.rumors.generate_rumors(session.id, "a")
    gm.rumors.append_for_turn(
        session,
        "a",
        distortion=0.6,
        budget=LlmBudget(8),
        max_new=8,
        max_active=50,
        min_source_support=0.3,
    )
    # Region A has no canonical knowledge here, so the deed rumor is the only candidate
    # source: with the rule, nothing is drafted from it (without the rule it would be).
    assert all(seed.statement not in prompt for prompt in rumor_llm.sources)


# --- EX-13: recent deeds reach the event suggestion ---------------------------------- #
def test_ex13_recent_deeds_are_in_the_suggestion_context() -> None:
    repo, gm, session, _p, voice, _r, _w = _setup()
    _tell(gm, voice, session)
    seen = {}

    class _Suggest:
        def structured(self, prompt, schema, *, system=None):
            seen["prompt"] = prompt
            return EventDraftList()

        def complete(self, prompt, *, system=None):  # pragma: no cover
            return ""

    gm.events._suggester = EventSuggester(_Suggest())
    gm.events.suggest_events(session.id, n=1)
    assert "Ari caught a thief." in seen["prompt"]
    assert "retold: The traveler caught a thief in the square!" in seen["prompt"]


# --- EX-19: a run that never advanced takes its deeds with it ------------------------ #
def test_ex19_a_failed_move_and_a_failed_declaration_leave_no_deeds() -> None:
    repo, gm, session, player, *_ = _setup()

    def boom(*args, **kwargs):
        raise RuntimeError("turn failed")

    gm.turns._one_turn = boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        gm.turns.advance(session.id, MoveAction(to_region_id="b"))
    assert repo.get_player(session.id).region_id == "a"
    assert [d.region_id for d in repo.list_deeds(session.id)] == ["a"]  # only the start
    with pytest.raises(RuntimeError):
        gm.turns.advance(session.id, DeclareAction(text="sing"))
    assert [d.kind for d in repo.list_deeds(session.id)] == ["arrival"]
    assert repo.get_player(session.id).turns_spent == 0
    assert any(e.kind == "action_declared" for e in repo.list_timeline(session.id))  # audit


def test_review_u6_4_a_failed_endtalk_takes_back_its_appraisals_of_earlier_deeds() -> None:
    """BR-U6-36 + review U6 #4: the EndTalk run's preparation saved Mara's appraisal of
    the declaration (an earlier deed); the run never advanced, so that appraisal goes too,
    the declaration is pending for her again and nothing is seeded from the undone talk."""
    repo, gm, session, _player, voice, *_ = _setup()
    gm.turns.advance(session.id, DeclareAction(text="도둑을 잡는다"), lang="ko")
    gm.dialogue.say(session.id, "n1", "I caught a thief!")
    voice.appraisal = AppraisalDraft(
        summary="Ari says Ari caught a thief.",
        appraisals=[
            AppraisalDraftItem(
                ref="d2",
                noteworthy=True,
                salience=1.0,
                slant="admiring",
                retelling="The traveler caught a thief in the square!",
            )
        ],
    )
    real = gm.turns._one_turn

    def boom(*args, **kwargs):
        raise RuntimeError("turn failed")

    gm.turns._one_turn = boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        gm.turns.advance(session.id, EndTalkAction(npc_id="n1"))
    assert repo.list_appraisals(session.id) == []
    declared = next(d for d in repo.list_deeds(session.id) if d.kind == "declared_action")
    player = repo.get_player(session.id)
    assert declared.id in {d.id for d in gm.deeds.pending_for(session.id, player, "n1")}
    gm.turns._one_turn = real  # type: ignore[method-assign]
    gm.turns.advance(session.id, WaitAction())
    assert repo.list_rumors_by_origin(session.id, deed_id=declared.id, include_inactive=True) == []


# --- RumorService units (code-plan review R-07) ------------------------------------- #
def test_seed_spread_and_reserved_units() -> None:
    repo, gm, session, player, *_ = _setup()
    deed = repo.list_deeds(session.id)[0]
    from locus.play.models import DeedAppraisal

    ap = DeedAppraisal(
        session_id=session.id,
        deed_id=deed.id,
        npc_id="n1",
        noteworthy=True,
        salience=0.5,
        retelling="A stranger came.",
    )
    seed = gm.rumors.seed(session, deed, ap, distortion=0.3)
    assert (seed.statement, seed.origin_kind, seed.origin_appraisal_id) == (
        "A stranger came.",
        "deed",
        ap.id,
    )
    assert seed.support == pytest.approx(0.3) and seed.confidence == pytest.approx(0.7)
    hop = gm.rumors.spread(
        session,
        seed,
        SpreadTarget(region_id="b", from_region_id="a", weight=0.6, degree=0.4, support=0.24),
    )
    assert (hop.region_id, hop.spread_from_region_id, hop.origin_deed_id) == ("b", "a", deed.id)
    assert hop.distorted_from_id == seed.id and hop.support == pytest.approx(0.24)
    full = gm.rumors.append_for_turn(
        session, "a", distortion=0.5, budget=LlmBudget(8), max_new=2, max_active=1, reserved=1
    )
    assert full == ([], "capped")


def test_a_failed_hop_returns_none() -> None:
    _repo, gm, session, _p, _v, rumor_llm, _w = _setup()
    rumor_llm.fail = True
    parent = deed_rumor("a").model_copy(update={"session_id": session.id})
    assert (
        gm.rumors.spread(
            session,
            parent,
            SpreadTarget(region_id="b", from_region_id="a", weight=0.6, degree=0.4, support=0.24),
        )
        is None
    )


def test_endtalk_without_new_words_judges_nothing() -> None:
    repo, gm, session, _p, voice, *_ = _setup()
    gm.turns.advance(session.id, EndTalkAction(npc_id="n1"))
    assert voice.structured_calls == [] and repo.list_appraisals(session.id) == []
    assert DeedKind.STATEMENT.value not in {d.kind for d in repo.list_deeds(session.id)}


# --- U7 Step 5.5: U6 review #8, #9, #14 and the scene's source hiding -------------- #
def test_review_u6_14_an_empty_declaration_is_400_even_while_a_turn_runs() -> None:
    """BR-U6-5: the rule lives in validate_action, so `act` answers 400 before the guard."""
    _repo, gm, session, _player, *_ = _setup()
    gm.guard.acquire(session.id, "someone-else")
    try:
        with pytest.raises(InvalidActionError):
            gm.play.act(session.id, DeclareAction(text="   "))
        with pytest.raises(InvalidActionError):
            gm.play.act(session.id, DeclareAction(text="x" * 301))
    finally:
        gm.guard.release(session.id)


def test_review_u6_8_a_turn_committed_before_the_guard_is_not_counted_as_ours() -> None:
    """The run's start turn is read under the guard: a GM turn that lands between the
    first read and the acquire must not shorten the refund of a run that then fails."""
    repo, gm, session, _player, *_ = _setup()
    real_acquire = gm.guard.acquire

    def acquire_after_a_gm_turn(session_id, run_id):
        repo.bump_turn(session_id)  # another run committed a turn in the gap
        return real_acquire(session_id, run_id)

    def boom(*args, **kwargs):
        raise RuntimeError("turn failed")

    gm.guard.acquire = acquire_after_a_gm_turn  # type: ignore[method-assign]
    gm.turns._one_turn = boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        gm.turns.advance(session.id, MoveAction(to_region_id="b"))
    player = repo.get_player(session.id)
    assert (player.region_id, player.turns_spent) == ("a", 0)  # full refund, put back
    assert [d.region_id for d in repo.list_deeds(session.id)] == ["a"]  # arrival undone


def test_review_u6_9_a_scene_read_error_fails_the_run_not_the_llm() -> None:
    repo, gm, session, _player, voice, *_ = _setup()

    def down(*args, **kwargs):
        raise RuntimeError("storage down")

    gm.turns._region_knowledge.region_sources = down  # type: ignore[union-attr]
    with pytest.raises(RuntimeError, match="storage down"):
        gm.turns.advance(session.id, DeclareAction(text="sing"), lang="ko")
    assert voice.structured_calls == []  # no narration call was booked
    assert repo.get_player(session.id).turns_spent == 0  # refunded: the run failed
    assert not [d for d in repo.list_deeds(session.id) if d.kind == "declared_action"]


def test_review_u6_1_the_narration_scene_hides_a_source_the_region_knows_distorted() -> None:
    """The narration record becomes deed text, so its scene follows BR-U5-11 too."""
    from locus.play.models import SessionRumor
    from locus.shared.models import (
        Knowledge,
        KnowledgeGraph,
        Provenance,
        ScopeLink,
        ScopeType,
        SourceKind,
    )

    ks, scopes = [], []
    for kid, text in (("k-fire", "The market burned."), ("k-bread", "Bread is cheap here.")):
        k = Knowledge(
            world_id="w", statement=text, title=kid, provenance=Provenance(source=SourceKind.INPUT)
        )
        k.id = kid
        ks.append(k)
        scopes.append(
            ScopeLink(world_id="w", knowledge_id=kid, region_id="a", scope_type=ScopeType.DIRECT)
        )
    world = build_snapshot(
        ["a", "b"],
        [edge("a", "b", weight=0.6)],
        npcs=[npc("n1", "a", name="Mara")],
        kg=KnowledgeGraph(world_id="w", knowledge=ks, scopes=scopes),
    )
    prompts: list[str] = []

    class Voice(VoiceLLM):
        def structured(self, prompt, schema, *, system=None):
            prompts.append(prompt)
            return super().structured(prompt, schema, system=system)

    repo = InMemoryPlayRepository()
    watch = _Watch()
    gm = compose_play(
        repo, RumorGenerator(RumorLLM(watch)), StaticSnapshots(world), dialogue_llm=Voice(watch)
    )
    session, _p = gm.sessions.start("w", PlayerCreate(name="Ari", start_region_id="a"))
    repo.upsert_rumors(
        [
            SessionRumor(
                session_id=session.id,
                region_id="a",
                distorted_from_id="k-fire",
                distorted_from_kind="knowledge",
                statement="Rioters set the market alight.",
                distortion_degree=0.6,
                support=0.5,
                provenance=Provenance(source=SourceKind.SIMULATION),
            )
        ]
    )
    gm.turns.advance(session.id, DeclareAction(text="sing"), lang="ko")
    scene = prompts[0]
    assert "Rioters set the market alight." in scene and "Bread is cheap here." in scene
    assert "The market burned." not in scene
