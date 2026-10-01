"""U3's carry of U7 review items into play (BR-U3-38, U7 review #9; plan Step 7)."""

from __future__ import annotations

import pytest

from locus.play import InMemoryPlayRepository
from locus.play.models import EventCategory, EventStatus, TimelineKind
from locus.play.rumor.dynamics import region_feedback, settle
from locus.play.rumor.generator import RumorGenerator
from tests.play.helpers import compose_play
from tests.play.test_play_services import _FakeLLM, _FakeLoader


def _setup():
    repo = InMemoryPlayRepository()
    loader = _FakeLoader()
    gm = compose_play(repo, RumorGenerator(_FakeLLM()), loader)
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, loader.region.id, 0.3)
    return repo, loader, gm, session


def _war_with_contribution(repo, gm, session, region_id: str, applied: float):
    event = gm.events.create_event(session.id, region_id, category=EventCategory.WAR, magnitude=0.8)
    event.contributions = {region_id: applied}
    repo.update_event(event)
    repo.set_region_distortion(session.id, region_id, 0.3 + applied)
    return event


def test_ex12_gm_set_clears_active_event_contributions() -> None:
    """EX-12 (BR-U3-38): 0.3 -> war 0.6 (contribution 0.3) -> GM 0.5 -> resolve -> 0.5."""
    repo, loader, gm, session = _setup()
    rid = loader.region.id
    event = _war_with_contribution(repo, gm, session, rid, 0.3)
    gm.distortions.set_region_distortion(session.id, rid, 0.5)
    line = repo.list_timeline(session.id)[-1]
    assert line.kind == TimelineKind.SET_DISTORTION.value
    assert line.payload["event_contributions_cleared"] == 0.3
    assert repo.get_event(session.id, event.id).contributions == {}
    gm.events.resolve_event(session.id, event.id)
    assert repo.get_region_distortion(session.id, rid) == 0.5


def test_gm_set_and_its_event_clearing_roll_back_together(monkeypatch) -> None:
    """One unit of work: a failing timeline write leaves the degree and the event as
    they were."""
    repo, loader, gm, session = _setup()
    rid = loader.region.id
    event = _war_with_contribution(repo, gm, session, rid, 0.3)

    def boom(*_a, **_k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(InMemoryPlayRepository, "append_timeline", boom)
    with pytest.raises(RuntimeError):
        gm.distortions.set_region_distortion(session.id, rid, 0.5)
    monkeypatch.undo()
    assert repo.get_region_distortion(session.id, rid) == pytest.approx(0.6)
    assert repo.get_event(session.id, event.id).contributions == {rid: 0.3}


def test_resolved_and_suggested_events_keep_their_contributions() -> None:
    repo, loader, gm, session = _setup()
    rid = loader.region.id
    event = _war_with_contribution(repo, gm, session, rid, 0.2)
    event.status = EventStatus.SUGGESTED
    repo.update_event(event)
    gm.distortions.set_region_distortion(session.id, rid, 0.4)
    assert repo.get_event(session.id, event.id).contributions == {rid: 0.2}
    assert repo.list_timeline(session.id)[-1].payload["event_contributions_cleared"] == 0.0


def test_support_settles_so_a_slider_value_meets_the_threshold() -> None:
    """U7 review #9: 0.35 + 0.1 is 0.45 and counts as strong at 0.45."""
    assert 0.35 + 0.1 < 0.45 and settle(0.35 + 0.1) == 0.45
    repo, loader, gm, session = _setup()
    r = gm.rumors.generate_rumors(session.id, loader.region.id)[0]
    gm.rumors.adjust_support(session.id, r.id, 0.35)
    rumor = repo.get_rumor(session.id, r.id)
    from locus.play.event.dynamics import evolve_support

    evolve_support([rumor], {loader.region.id}, reinforce=0.1)
    assert rumor.support == 0.45
    assert region_feedback([rumor], weight=0.1, high_support_threshold=0.45)


# --------------------------------------------------------------------------- #
# Event suggestion and world state (U7 review #13·#14·#15, §3, C11, C13)
# --------------------------------------------------------------------------- #
from locus.play.event import suggest_context as ctx  # noqa: E402
from locus.play.event.suggester import EventDraft, EventSuggester  # noqa: E402
from locus.shared.config.tuning import PlayTuning  # noqa: E402
from locus.shared.models import RegionBrief  # noqa: E402
from tests.play.strategies import build_snapshot  # noqa: E402
from tests.play.test_gm_events import _gm, _SuggestLLM  # noqa: E402
from tests.shared.snapshots import StaticSnapshots  # noqa: E402


def test_an_approved_event_is_active_in_state_and_prompt_in_memory() -> None:
    """#13: approve() stores an enum member in memory; state and prompt still see it."""
    repo, gm, session, llm = _gm([EventDraft(region_id="a", category="war", magnitude=0.5)])
    (event,) = gm.events.suggest_events(session.id)
    gm.events.approve_event(session.id, event.id)
    state = gm.world_state.state(session.id)
    assert {r.region_id: r.active_events for r in state.regions}["a"] == 1
    gm.events.suggest_events(session.id)
    prompt = llm.calls[-1][0]
    assert "EventStatus" not in prompt and "war m=0.5 active" in prompt


def test_state_carries_the_server_suggestion_cap() -> None:
    """#15: the GM screen reads the cap instead of assuming 1..5."""
    repo, gm, session, _llm = _gm()
    assert gm.world_state.state(session.id).max_event_suggestions == 5
    world = build_snapshot(["a"], [])
    tight = compose_play(
        InMemoryPlayRepository(),
        RumorGenerator(_FakeLLM()),
        StaticSnapshots(world),
        tuning=PlayTuning(max_event_suggestions=3),
    )
    s = tight.sessions.start_session("w")
    assert tight.world_state.state(s.id).max_event_suggestions == 3


def _brief(i: int, *, full: bool = True) -> RegionBrief:
    pad = "x" * 500 if full else ""
    return RegionBrief(
        region_id=f"r{i:02d}",
        name=f"N{i}{pad}",
        level="town",
        level_path=[f"P{pad}", f"N{i}"],
        description=pad or None,
        top_knowledge=[pad or "k", pad or "k2"],
    )


def test_context_keeps_events_and_deeds_whatever_the_region_count() -> None:
    """#14: regions fill what is left, whole lines; events and deeds always fit."""
    regions = [_brief(i) for i in range(60)]
    events = [ctx.event_line("Town", "war", 0.5, "active", "e" * 400) for _ in range(5)]
    deeds = [ctx.deed_line("Town", "d" * 900) for _ in range(5)]
    text = ctx.suggestion_context(regions, events, deeds)
    assert len(text) <= ctx.CONTEXT_MAX
    lines = text.splitlines()
    assert all(e in lines for e in events) and all(d in lines for d in deeds)
    shown = [line for line in lines if line.startswith("- r")]
    assert shown and all(line in {ctx.region_line(b) for b in regions} for line in shown)


def test_a_suggestion_in_a_region_the_prompt_left_out_is_kept() -> None:
    """§3: the draft's region is checked against the world, not only the shown lines."""
    world = build_snapshot(["a", "b"], [])
    llm = _SuggestLLM([EventDraft(region_id=r, category="war", magnitude=0.3) for r in "ab"])
    repo = InMemoryPlayRepository()
    gm = compose_play(
        repo,
        RumorGenerator(llm),
        StaticSnapshots(world),
        suggester=EventSuggester(llm),
        tuning=PlayTuning(suggest_max_regions=1),
    )
    session = repo.create_session("w")
    made = gm.events.suggest_events(session.id, n=2)
    assert sorted(e.region_id for e in made) == ["a", "b"]


def test_a_world_without_regions_does_not_call_the_suggester() -> None:
    """§3: no shown region -> [] before any LLM call."""
    llm = _SuggestLLM([EventDraft(region_id="a", category="war", magnitude=0.3)])
    repo = InMemoryPlayRepository()
    gm = compose_play(
        repo,
        RumorGenerator(llm),
        StaticSnapshots(build_snapshot([], [])),
        suggester=EventSuggester(llm),
    )
    session = repo.create_session("w")
    assert gm.events.suggest_events(session.id) == [] and llm.calls == []


def test_leaves_come_before_parents_and_terrain_sorts_by_depth() -> None:
    """§3: (parent?, -depth, name) for the rest; an unranked terrain leaf is not put
    before every town."""
    parent = RegionBrief(region_id="town", name="Town", level="town", level_path=["W", "Town"])
    leaf = RegionBrief(
        region_id="mill", name="Mill", level="district", level_path=["W", "Town", "Mill"]
    )
    terrain = RegionBrief(region_id="moor", name="Moor", level="terrain", level_path=["W", "Moor"])
    order = ctx.pick_brief_regions(
        [terrain, parent, leaf],
        player_region_id=None,
        event_region_ids=set(),
        rumor_counts={},
        limit=3,
        parent_ids={"town"},
    )
    assert [b.region_id for b in order] == ["mill", "moor", "town"]


def test_long_region_ids_are_shown_whole_and_names_match_by_name_key() -> None:
    """§3 ID_MAX and C13 (normalize_name)."""
    long_id = "r" * 100
    brief = RegionBrief(region_id=long_id, name="River ton", level="town")
    assert long_id in ctx.region_line(brief)
    assert ctx.match_region(long_id, [brief]) == long_id
    assert ctx.match_region("  river  TON ", [brief]) == long_id


# --------------------------------------------------------------------------- #
# Engine and reads (U7 review C2·C3·C4·C6, §3 names)
# --------------------------------------------------------------------------- #
from locus.play.base import region_name  # noqa: E402
from locus.play.models import Deed, DeedKind, PlayerCreate, SessionRumor  # noqa: E402
from locus.play.rumor.spread import neighbour_map  # noqa: E402
from locus.shared.models import ConnectionEdge, ConnectionKind  # noqa: E402
from locus.shared.models import Provenance as _Prov  # noqa: E402
from locus.shared.models import SourceKind as _Src  # noqa: E402


def _rumor(session_id: str, region_id: str, **kw) -> SessionRumor:
    return SessionRumor(
        session_id=session_id,
        region_id=region_id,
        distorted_from_id="k",
        statement="s",
        provenance=_Prov(source=_Src.SIMULATION),
        **kw,
    )


def test_a_line_about_a_vanished_region_names_it_by_id() -> None:
    """C4: one rule — the name, else the id (FR-D3)."""
    assert region_name({"a": "Riverton"}, "a") == "Riverton"
    assert region_name({}, "gone") == "gone"
    repo, _loader, gm, session = _setup()
    r = repo.upsert_rumor(_rumor(session.id, "gone"))
    gm.rumors.adjust_support(session.id, r.id, 0.5)
    line = repo.list_timeline(session.id)[-1]
    assert line.payload["region_name"] == "gone" and "in gone" in line.summary


def test_deed_voided_line_carries_region_names() -> None:
    """§3: the void line names its regions too."""
    repo, loader, gm, session = _setup()
    deed = repo.record_deed(
        Deed(
            session_id=session.id,
            player_id="p",
            region_id=loader.region.id,
            kind=DeedKind.ARRIVAL,
            text="arrived",
        )
    )
    repo.upsert_rumor(
        _rumor(session.id, loader.region.id, origin_kind="deed", origin_deed_id=deed.id)
    )
    gm.deeds.void(session.id, deed.id)
    payload = repo.list_timeline(session.id)[-1].payload
    assert payload["region_ids"] == [loader.region.id]
    assert payload["region_names"] == [loader.region.name]


def test_player_log_limit_keeps_the_newest_lines() -> None:
    """C6: ``limit`` cuts after the player filter."""
    repo, loader, gm, _session = _setup()
    session, _player = gm.sessions.start(
        "w", PlayerCreate(name="Ann", start_region_id=loader.region.id)
    )
    full = gm.play.log(session.id)
    assert full and gm.play.log(session.id, limit=1) == full[-1:]
    assert gm.play.log(session.id, limit=1000) == full


def test_neighbour_map_keeps_the_strongest_parallel_edge_and_drops_self_loops() -> None:
    """C3: one neighbour rule for the engine and the planner's fallback."""

    def edge(a, b, w, kind=ConnectionKind.ROUTE):
        return ConnectionEdge(
            world_id="w",
            source_region_id=a,
            target_region_id=b,
            kind=kind,
            weight=w,
            provenance=_Prov(source=_Src.INPUT),
        )

    near = neighbour_map(
        [edge("a", "b", 0.2), edge("a", "b", 0.9, ConnectionKind.RIVER), edge("a", "a", 1.0)]
    )
    assert near == {"a": {"b": 0.9}}


def test_region_knowledge_reads_active_rumors_only_without_lineage() -> None:
    """C2: the player screen and the session query skip inactive rows."""
    repo, loader, gm, session = _setup()
    repo.upsert_rumor(_rumor(session.id, loader.region.id))
    repo.upsert_rumor(_rumor(session.id, loader.region.id, active=False))
    rk = gm.region_knowledge
    assert len(rk.region_sources(session.id, loader.region.id).lineage) == 2
    assert len(rk.region_sources(session.id, loader.region.id, lineage=False).lineage) == 1


# --------------------------------------------------------------------------- #
# Dialogue and storage (U7 review §3 say, C14, C17, C18)
# --------------------------------------------------------------------------- #
def test_a_prompt_bug_in_say_is_not_reported_as_the_provider(monkeypatch) -> None:
    """§3: only the provider call maps to 503; building the prompt is ours."""
    from locus.play.errors import LlmCallFailedError
    from locus.play.npc import dialogue as dialogue_module
    from tests.play.test_dialogue import _setup as dialogue_setup

    _repo, gm, _snap, _llm, session, _player = dialogue_setup()
    gm.dialogue.start(session.id, "n1")

    def broken(*_a, **_k):
        raise KeyError("template field")

    monkeypatch.setattr(dialogue_module, "user_prompt", broken)
    with pytest.raises(KeyError):
        gm.dialogue.say(session.id, "n1", "hello")
    with pytest.raises(KeyError):  # not LlmCallFailedError
        try:
            gm.dialogue.say(session.id, "n1", "hello")
        except LlmCallFailedError:  # pragma: no cover - the bug being guarded
            pytest.fail("a prompt bug became a provider 503")


def test_one_line_text_is_cut_one_way() -> None:
    """C14: the deed line and the narration record use ``one_line(…, cap)``."""
    from locus.play.gm.narrator import fallback

    line = ctx.deed_line("Town", "d" * 900)
    assert len(line) == ctx.DEED_LINE_MAX and line == line.strip()
    record = fallback(declaration="x\n" * 900, player_name="Ann", lang="en").record
    assert "\n" not in record and len(record) <= 700


@pytest.fixture(params=["memory", "sql"])
def any_repo(request):
    if request.param == "memory":
        return InMemoryPlayRepository()
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine

    from locus.play.storage.postgres_repo import PostgresPlayRepository

    r = PostgresPlayRepository(engine=create_engine("sqlite://", future=True))
    r.ensure_schema()
    return r


def test_whitespace_only_retellings_are_no_retelling_in_both_adapters(any_repo) -> None:
    """C17: tabs, newlines, NBSP and U+3000 count as nothing to tell everywhere."""
    from locus.play.models import DeedAppraisal

    s = any_repo.create_session("w")
    deed = any_repo.record_deed(
        Deed(session_id=s.id, player_id="p", region_id="a", kind=DeedKind.ARRIVAL, text="came")
    )
    blanks = ["\t", "\n", " ", "　", " \t\n "]
    any_repo.save_appraisals(
        [
            DeedAppraisal(
                session_id=s.id,
                deed_id=deed.id,
                npc_id=f"n{i}",
                noteworthy=True,
                salience=0.9,
                retelling=text,
            )
            for i, text in enumerate(blanks)
        ]
        + [
            DeedAppraisal(
                session_id=s.id,
                deed_id=deed.id,
                npc_id="told",
                noteworthy=True,
                salience=0.9,
                retelling="  she came  ",
            )
        ]
    )
    got = any_repo.seed_candidates(s.id, min_salience=0.5)
    assert [(a.npc_id, a.retelling) for _d, a in got] == [("told", "she came")]


def test_a_plus_nine_timestamp_round_trips_through_sqlite() -> None:
    """C18: written as UTC, read back as the same instant."""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import create_engine

    from locus.play.storage.postgres_repo import PostgresPlayRepository

    repo = PostgresPlayRepository(engine=create_engine("sqlite://", future=True))
    repo.ensure_schema()
    s = repo.create_session("w")
    seoul = timezone(timedelta(hours=9))
    when = datetime(2026, 10, 1, 18, 0, tzinfo=seoul)
    deed = repo.record_deed(
        Deed(
            session_id=s.id,
            player_id="p",
            region_id="a",
            kind=DeedKind.STATEMENT,
            text="said",
            messages_through=when,
        )
    )
    back = repo.get_deed(s.id, deed.id)
    assert back is not None and back.messages_through == when
    assert back.messages_through.utcoffset() == timedelta(0)


# --- U3 code review #11 ------------------------------------------------------- #
def test_a_turn_reads_the_world_after_it_takes_the_guard() -> None:
    """U3 review #11: an editor region delete holds the session leases while it writes.
    A turn reads the world snapshot only after it took the guard, so a move is never
    checked against a world read before a delete that finished in between."""
    from locus.play.models import MoveAction
    from tests.play.test_player_mode import _engine

    _repo, _gm, turns, session, _player = _engine()
    order: list[str] = []
    acquire, read = turns.guard.acquire, turns._snapshots.get

    def guarded(*args, **kwargs):
        order.append("acquire")
        return acquire(*args, **kwargs)

    def snapshot(world_id):
        order.append("snapshot")
        return read(world_id)

    turns.guard.acquire = guarded  # type: ignore[method-assign]
    turns._snapshots.get = snapshot  # type: ignore[method-assign]
    turns._start(session.id, MoveAction(to_region_id="b"))
    try:
        assert order[:2] == ["acquire", "snapshot"]
    finally:
        turns.guard.release(session.id)
