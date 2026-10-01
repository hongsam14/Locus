"""U6 DeedService — stays, pending deeds, seeds, memories, recent, views and void
(Step 5.5): EX-1, EX-10, EX-16, TP-U6-3, TP-U6-5 and the record_appraisal store."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from locus.play import InMemoryPlayRepository
from locus.play.deeds.service import DeedService
from locus.play.errors import AppraisalExistsError
from locus.play.models import (
    AppraisalOutcome,
    Deed,
    DeedAppraisal,
    DeedKind,
    Narration,
    Player,
    TurnRun,
)
from locus.shared.config.tuning import PlayTuning
from tests.play.strategies import build_snapshot, deed_rumor, edge, npc
from tests.shared.snapshots import StaticSnapshots

WORLD = build_snapshot(
    ["a", "b"],
    [edge("a", "b", weight=0.6)],
    npcs=[npc("n1", "a", name="Mara"), npc("n3", "a", name="Tom"), npc("n2", "b", name="Bo")],
)


def _setup(tuning: PlayTuning | None = None):
    repo = InMemoryPlayRepository()
    deeds = DeedService(repo, StaticSnapshots(WORLD), tuning=tuning or PlayTuning())
    session = repo.create_session("w")
    player = repo.create_player(Player(session_id=session.id, name="Ari", region_id="a"))
    return repo, deeds, session, player


def _arrive(repo, deeds, session, player, region_id, run_id=None) -> Deed:
    player.region_id = region_id
    repo.update_player(player)
    with repo.uow() as u:
        return deeds.arrival(
            u, session, player, WORLD.regions_by_id[region_id], WORLD, run_id=run_id
        )


def _deed(
    repo,
    session,
    player,
    kind=DeedKind.DECLARED_ACTION,
    text="Ari sang.",
    witnesses=("n1", "n3"),
    region="a",
) -> Deed:
    return repo.record_deed(
        Deed(
            session_id=session.id,
            player_id=player.id,
            region_id=region,
            kind=kind,
            text=text,
            witnessed_npc_ids=list(witnesses),
        )
    )


def _ap(session, deed, npc_id, *, noteworthy=True, salience=0.8, retelling="They say Ari sang."):
    return DeedAppraisal(
        session_id=session.id,
        deed_id=deed.id,
        npc_id=npc_id,
        noteworthy=noteworthy,
        salience=salience,
        retelling=retelling if noteworthy else "",
    )


# --- EX-1 / BR-U6-1/2: arrivals ----------------------------------------------------- #
def test_ex1_an_arrival_is_witnessed_by_everyone_here() -> None:
    repo, deeds, session, player = _setup()
    d = _arrive(repo, deeds, session, player, "a", run_id="run-1")
    assert (d.kind, d.text, d.witnessed_npc_ids, d.run_id) == (
        "arrival",
        "Ari arrived in A.",
        ["n1", "n3"],
        "run-1",
    )


# --- BR-U6-4 / EX-16: the stay ------------------------------------------------------ #
def test_ex16_voiding_this_stays_arrival_never_revives_the_old_stay() -> None:
    repo, deeds, session, player = _setup()
    _arrive(repo, deeds, session, player, "a")
    old = _deed(repo, session, player, text="Ari sang in A.")
    _arrive(repo, deeds, session, player, "b")
    back = _arrive(repo, deeds, session, player, "a")
    assert [d.id for d in deeds.current_stay(session.id, player)] == [back.id]
    back.voided = True
    repo.update_deed(back)
    stay = deeds.current_stay(session.id, player)
    assert stay == [] and old.id not in {d.id for d in stay}


def test_pending_deeds_are_witnessed_unjudged_and_capped_newest_first() -> None:
    repo, deeds, session, player = _setup(PlayTuning(appraisal_max_deeds=2))
    arrival = _arrive(repo, deeds, session, player, "a")
    sang = _deed(repo, session, player, text="Ari sang.")
    unseen = _deed(repo, session, player, text="Ari hid.", witnesses=("n3",))
    danced = _deed(repo, session, player, text="Ari danced.")
    repo.save_appraisals([_ap(session, danced, "n1")])
    pending = deeds.pending_for(session.id, player, "n1")
    assert [d.id for d in pending] == [arrival.id, sang.id]  # newest 2 unjudged, in order
    assert unseen.id not in {d.id for d in pending}


# --- TP-U6-3: seeds_ready against an independent filter ----------------------------- #
@settings(max_examples=60)
@given(
    rows=st.lists(
        st.tuples(st.booleans(), st.floats(0.0, 1.0), st.booleans(), st.booleans(), st.booleans()),
        min_size=1,
        max_size=8,
    )
)
def test_tp_u6_3_seeds_ready_is_exactly_the_eligible_appraisals(rows) -> None:
    repo, deeds, session, player = _setup()
    expected = set()
    for i, (noteworthy, salience, retold, seeded, voided) in enumerate(rows):
        d = _deed(repo, session, player, text=f"deed {i}")
        if voided:
            d.voided = True
            repo.update_deed(d)
        (a,) = repo.save_appraisals(
            [
                DeedAppraisal(
                    session_id=session.id,
                    deed_id=d.id,
                    npc_id="n1",
                    noteworthy=noteworthy,
                    salience=salience,
                    retelling="told" if retold else "",
                )
            ]
        )
        if seeded:
            repo.mark_seeded(session.id, a.id, f"r{i}")
        if noteworthy and salience >= 0.5 and retold and not seeded and not voided:
            expected.add(a.id)
    got = [a.id for _d, a in deeds.seeds_ready(session.id)]
    assert set(got) == expected and len(got) == len(set(got))


# --- TP-U6-5 / BR-U6-30: an NPC's memories ------------------------------------------- #
def test_tp_u6_5_memories_are_own_judgements_and_unjudged_sights_never_voided() -> None:
    repo, deeds, session, player = _setup(PlayTuning(npc_max_deeds=5))
    arrival = _arrive(repo, deeds, session, player, "a")
    told = _deed(repo, session, player, text="Ari caught a thief.")
    others = _deed(repo, session, player, text="Ari bought bread.")
    void = _deed(repo, session, player, text="Ari burned a cart.")
    repo.save_appraisals(
        [
            _ap(session, told, "n1", retelling="The traveler caught a thief!").model_copy(
                update={"slant": "admiring"}
            ),
            _ap(session, others, "n3"),  # Tom's judgement, not Mara's
            _ap(session, void, "n1"),
        ]
    )
    void.voided = True
    repo.update_deed(void)
    mem = deeds.memories(session.id, player, "n1")
    by_id = {m.deed_id: m for m in mem}
    assert set(by_id) == {told.id, others.id, arrival.id}  # own + seen-unjudged, no void
    assert by_id[told.id].text == "The traveler caught a thief!"
    assert by_id[told.id].slant == "admiring"
    assert by_id[others.id].text == "Ari bought bread."  # Mara saw it, did not judge it


def test_memories_respect_the_limit_newest_first() -> None:
    repo, deeds, session, player = _setup(PlayTuning(npc_max_deeds=2))
    _arrive(repo, deeds, session, player, "a")
    _deed(repo, session, player, text="one")
    newer = _deed(repo, session, player, text="two")
    newest = _deed(repo, session, player, text="three")
    assert [m.deed_id for m in deeds.memories(session.id, player, "n1")] == [newest.id, newer.id]


def test_recent_skips_voided_and_is_newest_first() -> None:
    repo, deeds, session, player = _setup()
    a = _deed(repo, session, player, text="a")
    b = _deed(repo, session, player, text="b")
    c = _deed(repo, session, player, text="c")
    b.voided = True
    repo.update_deed(b)
    repo.save_appraisals([_ap(session, c, "n1")])
    recent = deeds.recent(session.id, 5)
    assert [d.id for d, _aps in recent] == [c.id, a.id]
    assert [ap.npc_id for ap in recent[0][1]] == ["n1"]


# --- EX-10 / BR-U6-27: void ---------------------------------------------------------- #
def test_ex10_void_turns_off_every_rumor_of_the_deed_and_is_idempotent() -> None:
    repo, deeds, session, player = _setup()
    d = _deed(repo, session, player)
    seed = deed_rumor("a", deed_id=d.id).model_copy(update={"session_id": session.id})
    hop = deed_rumor("b", deed_id=d.id).model_copy(
        update={"session_id": session.id, "promoted": True, "spread_from_region_id": "a"}
    )
    other = deed_rumor("a", deed_id="other").model_copy(update={"session_id": session.id})
    repo.upsert_rumors([seed, hop, other])
    result = deeds.void(session.id, d.id)
    assert set(result.deactivated_rumor_ids) == {seed.id, hop.id}
    assert repo.get_deed(session.id, d.id).voided is True
    assert {r.id for r in repo.list_rumors(session.id)} == {other.id}
    assert deeds.void(session.id, d.id).deactivated_rumor_ids == []  # idempotent
    entry = [e for e in repo.list_timeline(session.id) if e.kind == "deed_voided"]
    assert len(entry) == 1 and entry[0].payload["region_ids"] == ["a", "b"]
    with pytest.raises(LookupError):
        deeds.void(session.id, "missing")


def test_views_show_reach_and_appraisals_newest_first() -> None:
    repo, deeds, session, player = _setup()
    older = _deed(repo, session, player, text="older")
    newer = _deed(repo, session, player, text="newer")
    repo.save_appraisals([_ap(session, newer, "n1")])
    repo.upsert_rumors(
        [
            deed_rumor("b", deed_id=newer.id).model_copy(
                update={"session_id": session.id, "active": False}
            )
        ]
    )
    views = deeds.views(session.id)
    assert [v.deed.id for v in views] == [newer.id, older.id]
    assert views[0].reached_region_ids == ["b"] and len(views[0].appraisals) == 1


# --- record_declaration / record_appraisal ------------------------------------------- #
def test_record_appraisal_stores_the_statement_its_judgement_and_the_timeline() -> None:
    repo, deeds, session, player = _setup()
    sang = _deed(repo, session, player)
    run = TurnRun(session_id=session.id)
    outcome = AppraisalOutcome(
        statement_text="Ari asked about the mill.",
        appraisals=[_ap(session, sang, "n1")],
        statement_appraisal=DeedAppraisal(
            session_id=session.id, deed_id="", npc_id="n1", noteworthy=False, salience=0.0
        ),
        llm_calls=1,
    )
    saved = deeds.record_appraisal(
        run, session, player, WORLD.regions_by_id["a"], WORLD.npcs_by_region["a"][0], outcome
    )
    statements = [d for d in repo.list_deeds(session.id) if d.kind == "statement"]
    assert len(statements) == 1 and statements[0].witnessed_npc_ids == ["n1"]
    assert statements[0].run_id == run.id
    assert {a.deed_id for a in saved} == {sang.id, statements[0].id}
    kinds = [e.kind for e in repo.list_timeline(session.id)]
    assert kinds.count("deed_recorded") == 1 and kinds.count("deed_appraised") == 2


def test_record_appraisal_drops_a_pair_written_meanwhile() -> None:
    """A write outside the turn guard (CLI, second worker) judged the same deed first."""
    repo, deeds, session, player = _setup()
    sang = _deed(repo, session, player)
    repo.save_appraisals([_ap(session, sang, "n1")])
    outcome = AppraisalOutcome(appraisals=[_ap(session, sang, "n1")])
    with pytest.raises(AppraisalExistsError):
        repo.save_appraisals([_ap(session, sang, "n1")])
    saved = deeds.record_appraisal(
        TurnRun(session_id=session.id),
        session,
        player,
        WORLD.regions_by_id["a"],
        WORLD.npcs_by_region["a"][0],
        outcome,
    )
    assert saved == [] and len(repo.list_appraisals(session.id)) == 1


def test_record_declaration_stores_the_english_record_and_the_narration_entry() -> None:
    repo, deeds, session, player = _setup()
    run = TurnRun(session_id=session.id)
    narration = Narration(text="광장이 술렁인다.", record="Ari caught a thief.", lang="ko")
    deed = deeds.record_declaration(
        run,
        session,
        player,
        WORLD.regions_by_id["a"],
        WORLD.npcs_by_region["a"],
        narration,
        "도둑을 잡는다",
    )
    assert (deed.text, deed.declaration, deed.witnessed_npc_ids, deed.run_id) == (
        "Ari caught a thief.",
        "도둑을 잡는다",
        ["n1", "n3"],
        run.id,
    )
    (entry,) = [e for e in repo.list_timeline(session.id) if e.kind == "action_declared"]
    assert entry.payload["narration"] == "광장이 술렁인다." and entry.payload["lang"] == "ko"
