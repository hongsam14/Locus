"""Augmentation Q&A (U7 FR-F; U3 BLM §4, BR-U3-22..28·41, TP-U3-4/5, EX-7/8/9).

U3 intended change (C-3, nfr §4): questions carry a target and fixed actions, answers
return ``AnswerResult``, a run keeps up to 30 answers (was 5 rounds), dangling means id
properties, unscoped is new, wiki_conflict reads ``terrain_kind``, undo is latest-first
and refused after an outside edit. Tests below that existed before U3 keep their names.
"""

from __future__ import annotations

import threading
import time

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from locus.shared.models import (
    ConnectionEdge,
    ConnectionKind,
    Entity,
    EntityType,
    Knowledge,
    KnowledgeGraph,
    PriorType,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    ScopeType,
    SourceKind,
    WikiPrior,
    WorldMeta,
)
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.persistence import persist_graph
from locus.world.augmentation import (
    AugmentationEngine,
    AugmentationService,
    InMemoryRunStore,
    RunState,
)
from locus.world.augmentation.detectors import (
    connection_id,
    detect_dangling,
    detect_gaps,
    detect_low_confidence,
    detect_orphans,
    detect_unscoped,
)
from locus.world.augmentation.questions import ACTIONS, QuestionGenerator
from locus.world.augmentation.types import (
    AnswerAction,
    AugmentationAnswer,
    AugmentationRun,
    ChangeAlreadyRevertedError,
    IssueType,
    RevertConflictError,
    RevertOrderError,
    RunFinishedError,
    RunStatus,
)
from locus.world.refs import ConnectionKey
from locus.world.worldfile import WorldFile
from tests.shared.snapshots import snapshot_of
from tests.world.editor.helpers import Stack
from tests.world.strategies import editable_worlds

_PBT = settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _snap(kg: KnowledgeGraph, regions: list[Region] | None = None, connections=None):
    return snapshot_of(
        kg, RegionTopology(world_id="w", regions=regions or [], connections=connections or [])
    )


# --------------------------------------------------------------------------- #
# detectors (pure)
# --------------------------------------------------------------------------- #
def test_detect_gaps_empty_region_and_dangling() -> None:
    # U3 intended change: BR-U3-22/23 — the "relation to a missing entity" branch is gone
    # (the loader drops such edges); dangling now reads id properties
    a = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=_prov())
    child = Region(
        world_id="w", name="C", level=RegionLevel.TOWN, parent_id="gone", provenance=_prov()
    )
    k = Knowledge(world_id="w", statement="x", title="x", provenance=_prov())
    snap = _snap(KnowledgeGraph(world_id="w", knowledge=[k]), [a, child])
    assert {str(i.type) for i in detect_gaps(snap)} == {IssueType.GAP.value}
    dangling = detect_dangling(snap, set())
    assert [(i.target_ids, i.field, i.broken_id) for i in dangling] == [
        ([child.id], "parent_id", "gone")
    ]


def test_detect_low_confidence() -> None:
    k = Knowledge(
        world_id="w", statement="maybe", title="maybe", confidence=0.3, provenance=_prov()
    )
    e = Entity(
        world_id="w", name="E", entity_type=EntityType.PLACE, confidence=0.2, provenance=_prov()
    )
    issues = detect_low_confidence(_snap(KnowledgeGraph(world_id="w", knowledge=[k], entities=[e])))
    assert len(issues) == 2
    assert all(str(i.type) == IssueType.LOW_CONFIDENCE.value for i in issues)
    assert {i.target_kind for i in issues} == {"knowledge", "entity"}


def test_detect_orphans() -> None:
    linked = Entity(
        world_id="w",
        name="Tower",
        entity_type=EntityType.PLACE,
        located_in="r1",
        provenance=_prov(),
    )
    orphan = Entity(
        world_id="w", name="Floating Rock", entity_type=EntityType.OBJECT, provenance=_prov()
    )
    issues = detect_orphans(_snap(KnowledgeGraph(world_id="w", entities=[linked, orphan])))
    assert len(issues) == 1
    assert str(issues[0].type) == IssueType.ORPHAN.value
    assert issues[0].target_ids == [orphan.id]


def test_detect_unscoped_skips_global_and_scoped() -> None:
    region = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=_prov())
    scoped, free, everywhere = (
        Knowledge(world_id="w", statement=s, title=s, is_global=g, provenance=_prov())
        for s, g in (("scoped", False), ("free", False), ("global", True))
    )
    kg = KnowledgeGraph(
        world_id="w",
        knowledge=[scoped, free, everywhere],
        scopes=[ScopeLink(world_id="w", knowledge_id=scoped.id, region_id=region.id)],
    )
    assert [i.target_ids for i in detect_unscoped(_snap(kg, [region]))] == [[free.id]]


def test_dangling_list_ids_are_one_issue_each_and_connections_one_per_pair() -> None:
    """FD 검토 02 R-11: two broken ids in one list -> two issues; a broken prior ref on
    a connection pair -> one issue."""
    a, b = (Region(world_id="w", name=n, level=RegionLevel.TOWN, provenance=_prov()) for n in "AB")
    pair = [
        ConnectionEdge(
            world_id="w",
            source_region_id=x.id,
            target_region_id=y.id,
            kind=ConnectionKind.ROUTE,
            wiki_prior_ref="lost",
            provenance=_prov(),
        )
        for x, y in ((a, b), (b, a))
    ]
    k = Knowledge(
        world_id="w",
        statement="s",
        title="t",
        derived_from_prior_ids=["p1", "x1", "x2"],
        about_entity_ids=["e?"],
        provenance=_prov(),
    )
    issues = detect_dangling(
        _snap(KnowledgeGraph(world_id="w", knowledge=[k]), [a, b], pair), {"p1"}
    )
    keys = {(i.target_kind, i.field, i.broken_id) for i in issues}
    assert keys == {
        ("connection", "wiki_prior_ref", "lost"),
        ("knowledge", "derived_from_prior_ids", "x1"),
        ("knowledge", "derived_from_prior_ids", "x2"),
        ("knowledge", "about_entity_ids", "e?"),
    }
    assert len({i.key for i in issues}) == 4
    conn = next(i for i in issues if i.target_kind == "connection")
    assert conn.target_ids == [connection_id(ConnectionKey.of(pair[1]))]


@st.composite
def _broken_worlds(draw):
    """A generated world with some id properties pointed at missing ids (TP-U3-5)."""
    file: WorldFile = draw(editable_worlds())
    gone = st.sampled_from(["gone-1", "gone-2"])
    regions = [
        r.model_copy(update={"parent_id": draw(gone)}) if draw(st.booleans()) else r
        for r in file.regions
    ]
    entities = [
        e.model_copy(update={"located_in": draw(gone)}) if draw(st.booleans()) else e
        for e in file.entities
    ]
    knowledge = [
        k.model_copy(
            update={
                "derived_from_prior_ids": k.derived_from_prior_ids
                + draw(st.lists(gone, max_size=2)),
                "about_entity_ids": k.about_entity_ids + draw(st.lists(gone, max_size=1)),
            }
        )
        for k in file.knowledge
    ]
    # A connection is a pair with one prior ref (BR-U3-10): both directions get the same
    # broken ref, as an edit or an import would leave them. Drawing per direction made
    # pairs the detector (one issue per pair) and this oracle count differently — a
    # flaky property (U3 review #7).
    refs: dict[str, str | None] = {}
    conns = []
    for c in file.connections:
        pair = connection_id(ConnectionKey.of(c))
        if pair not in refs:
            refs[pair] = draw(gone) if draw(st.booleans()) else None
        conns.append(c.model_copy(update={"wiki_prior_ref": refs[pair]}) if refs[pair] else c)
    kg = KnowledgeGraph(world_id="w", entities=entities, knowledge=knowledge, priors=file.priors)
    return _snap(kg, regions, conns)


@_PBT
@given(snap=_broken_worlds())
def test_tp_u3_5_dangling_matches_a_direct_count(snap) -> None:
    """TP-U3-5: the detector finds exactly the references to ids the world lacks,
    counted directly (lists by id, connections by pair)."""
    regions = set(snap.regions_by_id)
    entities = {e.id for e in snap.kg.entities}
    priors = {p.id for p in snap.kg.priors}
    oracle = {
        (r.id, "parent_id", r.parent_id)
        for r in snap.topo.regions
        if r.parent_id and r.parent_id not in regions
    }
    oracle |= {
        (e.id, "located_in", e.located_in)
        for e in snap.kg.entities
        if e.located_in and e.located_in not in regions
    }
    oracle |= {
        (connection_id(ConnectionKey.of(c)), "wiki_prior_ref", c.wiki_prior_ref)
        for c in snap.topo.connections
        if c.wiki_prior_ref and c.wiki_prior_ref not in priors
    }
    for k in snap.kg.knowledge:
        oracle |= {
            (k.id, "derived_from_prior_ids", p) for p in k.derived_from_prior_ids if p not in priors
        }
        oracle |= {(k.id, "about_entity_ids", e) for e in k.about_entity_ids if e not in entities}
    found = [(i.target_ids[0], i.field, i.broken_id) for i in detect_dangling(snap, priors)]
    assert len(found) == len(set(found)) and set(found) == oracle


def test_question_generator_template() -> None:
    # U3 intended change: BR-U3-24 — fixed actions and a named target (was ``options``)
    region = Region(world_id="w", name="Hollow", level=RegionLevel.TOWN, provenance=_prov())
    snap = _snap(KnowledgeGraph(world_id="w"), [region])
    issue = detect_gaps(snap)[0]
    (q,) = QuestionGenerator(llm=None).generate([issue], snap, polished={})
    assert q.issue_id == issue.id and q.issue_key == issue.key
    assert q.actions == ACTIONS[IssueType.GAP] and "Hollow" in q.text
    assert q.target is not None and q.target.name == "Hollow" and q.target.kind == "region"


# --------------------------------------------------------------------------- #
# A small world for the service (EX-7/8/9)
# --------------------------------------------------------------------------- #
def _seeded() -> tuple[Stack, dict]:
    stack = Stack()
    riverton = Region(
        world_id="w",
        name="Riverton",
        level=RegionLevel.TOWN,
        attributes={"terrain_kind": "river"},
        provenance=_prov(),
    )
    hollow = Region(world_id="w", name="Hollow", level=RegionLevel.TOWN, provenance=_prov())
    fish = Knowledge(
        world_id="w",
        statement="fish swim upstream",
        title="fish",
        confidence=0.3,
        provenance=_prov(),
    )
    lore = Knowledge(world_id="w", statement="an old song", title="song", provenance=_prov())
    tomas = Entity(
        world_id="w",
        name="Tomas",
        entity_type=EntityType.PERSON,
        located_in="gone",
        provenance=_prov(),
    )
    ghost = Entity(
        world_id="w",
        name="Ghost",
        entity_type=EntityType.PERSON,
        confidence=0.2,
        located_in=hollow.id,
        provenance=_prov(),
    )
    persist_graph(
        stack.graph,
        stack.search,
        None,
        "w",
        regions=[riverton, hollow],
        knowledge=[fish, lore],
        entities=[tomas, ghost],
        scopes=[
            ScopeLink(
                world_id="w",
                knowledge_id=fish.id,
                region_id=riverton.id,
                scope_type=ScopeType.DIRECT,
            )
        ],
        meta=WorldMeta(id="w", name="W"),
    )
    stack.cache.invalidate("w")
    return stack, {
        "riverton": riverton,
        "hollow": hollow,
        "fish": fish,
        "lore": lore,
        "tomas": tomas,
        "ghost": ghost,
    }


def _service(stack: Stack, **kw) -> AugmentationService:
    return AugmentationService(AugmentationEngine(stack.editors, **kw.pop("engine", {})), **kw)


def _question(run: AugmentationRun, kind: str, target_id: str, field: str | None = None):
    return next(
        q
        for q in run.open_questions
        if q.issue_key.startswith(kind + ":")
        and q.target
        and q.target.id == target_id
        and (field is None or q.target.field == field)
    )


def test_ex7_dangling_location_edit_and_remove() -> None:
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    q = _question(run, "dangling", w["tomas"].id, "located_in")
    assert q.target is not None and q.target.name == "Tomas" and q.target.broken_id == "gone"
    res = svc.answer(
        run.id, AugmentationAnswer(question_id=q.id, action="edit", ref_id=w["hollow"].id)
    )
    tomas = gm.node_to_entity(stack.graph.get_node("w", w["tomas"].id))  # type: ignore[arg-type]
    assert tomas.located_in == w["hollow"].id
    assert ("LOCATED_IN", w["tomas"].id, w["hollow"].id) in {
        (e.type, e.source_id, e.target_id) for e in stack.graph.get_edges("w")
    }
    assert [t.id for t in res.changed] == [w["tomas"].id]
    svc.revert(run.id, res.change.id)  # type: ignore[union-attr]
    run = svc.get_run(run.id)  # type: ignore[assignment]
    q = _question(run, "dangling", w["tomas"].id, "located_in")
    svc.answer(run.id, AugmentationAnswer(question_id=q.id, action="remove"))
    tomas = gm.node_to_entity(stack.graph.get_node("w", w["tomas"].id))  # type: ignore[arg-type]
    assert tomas.located_in is None


def test_dangling_edit_needs_a_reference_of_the_right_kind() -> None:
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    q = _question(run, "dangling", w["tomas"].id, "located_in")
    with pytest.raises(ValueError):  # an entity is not a region
        svc.answer(
            run.id, AugmentationAnswer(question_id=q.id, action="edit", ref_id=w["ghost"].id)
        )
    assert svc.get_run(run.id).answers == 0  # type: ignore[union-attr]


def test_ex8_entity_confirm_then_revert_once() -> None:
    """EX-8 / B3: an entity target is confirmed on the entity (no 500); the same run
    reverts it (no 404); a second revert is 409."""
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    q = _question(run, "low_confidence", w["ghost"].id)
    res = svc.answer(run.id, AugmentationAnswer(question_id=q.id, action="confirm"))
    ghost = gm.node_to_entity(stack.graph.get_node("w", w["ghost"].id))  # type: ignore[arg-type]
    assert ghost.confidence == 0.9
    change = res.change
    assert change is not None
    svc.revert(run.id, change.id)
    ghost = gm.node_to_entity(stack.graph.get_node("w", w["ghost"].id))  # type: ignore[arg-type]
    assert ghost.confidence == 0.2
    with pytest.raises(ChangeAlreadyRevertedError):
        svc.revert(run.id, change.id)


def test_ex9_gap_add_and_revert_leave_nothing() -> None:
    stack, w = _seeded()
    before = stack.state()
    svc = _service(stack)
    run = svc.start_run("w")
    q = _question(run, "gap", w["hollow"].id)
    with pytest.raises(ValueError):  # BR-U3-25: a statement is required
        svc.answer(run.id, AugmentationAnswer(question_id=q.id, action="add", statement="  "))
    res = svc.answer(
        run.id, AugmentationAnswer(question_id=q.id, action="add", statement="the well ran dry")
    )
    (new_id,) = res.change.added_ids  # type: ignore[union-attr]
    assert ("w", new_id) in stack.search.docs
    assert any(
        s.knowledge_id == new_id and s.region_id == w["hollow"].id
        for s in stack.cache.get("w").kg.scopes
    )
    svc.revert(run.id, res.change.id)  # type: ignore[union-attr]
    assert stack.state() == before


def test_answer_targets_the_question_not_the_sent_id() -> None:
    """B1: a ``target_id`` from the screen is ignored."""
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    q = _question(run, "low_confidence", w["fish"].id)
    svc.answer(
        run.id, AugmentationAnswer(question_id=q.id, action="remove", target_id=w["lore"].id)
    )
    assert stack.graph.get_node("w", w["fish"].id) is None
    assert stack.graph.get_node("w", w["lore"].id) is not None


def test_an_action_outside_the_question_is_refused() -> None:
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    q = _question(run, "gap", w["hollow"].id)
    with pytest.raises(ValueError):
        svc.answer(run.id, AugmentationAnswer(question_id=q.id, action="remove"))


# --------------------------------------------------------------------------- #
# Undo order and outside edits (BR-U3-27, FD 검토 R-08)
# --------------------------------------------------------------------------- #
def test_revert_is_latest_first_and_refused_after_an_outside_edit() -> None:
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    first = svc.answer(
        run.id,
        AugmentationAnswer(
            question_id=_question(run, "low_confidence", w["fish"].id).id, action="confirm"
        ),
    )
    run = first.run
    second = svc.answer(
        run.id,
        AugmentationAnswer(
            question_id=_question(run, "low_confidence", w["ghost"].id).id, action="confirm"
        ),
    )
    with pytest.raises(RevertOrderError):
        svc.revert(run.id, first.change.id)  # type: ignore[union-attr]
    # the ghost is edited on the editor screen after the run confirmed it
    ghost = gm.node_to_entity(stack.graph.get_node("w", w["ghost"].id))  # type: ignore[arg-type]
    stack.editors.entities.update_entity(ghost.model_copy(update={"description": "seen"}))
    before = stack.state()
    with pytest.raises(RevertConflictError):
        svc.revert(run.id, second.change.id)  # type: ignore[union-attr]
    assert stack.state() == before


def test_ignore_is_out_of_the_undo_order_and_can_be_asked_again() -> None:
    """R-08a: ignore counts as an answer, is not in the history, and unignore asks again;
    a run with nothing left converges, a stopped run refuses."""
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    keys = []
    while run.status == RunStatus.OPEN:
        q = run.open_questions[0]
        keys.append(q.issue_key)
        run = svc.answer(run.id, AugmentationAnswer(question_id=q.id, action="ignore")).run
    assert run.status == RunStatus.CONVERGED and run.history == []
    assert run.answers == len(keys) and run.ignored_keys == keys
    run = svc.unignore(run.id, keys[0])
    assert run.status == RunStatus.OPEN and run.answers == len(keys)
    assert keys[0] in {q.issue_key for q in run.open_questions}
    with pytest.raises(LookupError):
        svc.unignore(run.id, "not-ignored")

    stopped = _service(stack, max_answers=1)
    run = stopped.start_run("w")
    run = stopped.answer(
        run.id, AugmentationAnswer(question_id=run.open_questions[0].id, action="ignore")
    ).run
    assert run.status == RunStatus.STOPPED and run.open_questions == []
    with pytest.raises(RunFinishedError):
        stopped.unignore(run.id, run.ignored_keys[0])
    with pytest.raises(RunFinishedError):
        stopped.answer(run.id, AugmentationAnswer(question_id="q", action="ignore"))


@pytest.mark.parametrize("outside", ["weight", "kind", "delete", None])
def test_a_connection_answer_is_not_undone_over_an_outside_edit(outside) -> None:
    """U3 review #4 (BR-U3-27): an answer on a connection records no node, so undo
    checks the edges it wrote. An edit of that pair after the answer refuses the undo
    with nothing written; with no edit the undo puts the broken ref back."""
    stack, w = _seeded()
    prior = WikiPrior(
        world_id="w",
        prior_type=PriorType.FACT,
        condition="road",
        effect="carts pass",
        provenance=_prov(),
    )
    persist_graph(stack.graph, stack.search, None, "w", priors=[prior])
    stack.cache.invalidate("w")
    road = ConnectionEdge(
        world_id="w",
        source_region_id=w["riverton"].id,
        target_region_id=w["hollow"].id,
        kind=ConnectionKind.ROUTE,
        weight=0.5,
        rationale="old road",
        wiki_prior_ref="gone-prior",
        provenance=_prov(),
    )
    stack.editors.connections.upsert_connection(road)
    svc = _service(stack)
    run = svc.start_run("w")
    q = next(q for q in run.open_questions if q.target and q.target.field == "wiki_prior_ref")
    res = svc.answer(run.id, AugmentationAnswer(question_id=q.id, action="edit", ref_id=prior.id))
    assert res.change is not None
    key = ConnectionKey.of(road)
    if outside == "weight":
        stack.editors.connections.upsert_connection(
            road.model_copy(update={"wiki_prior_ref": prior.id, "weight": 0.9})
        )
    elif outside == "kind":
        stack.editors.connections.change_connection_kind(key, ConnectionKind.RIVER)
    elif outside == "delete":
        stack.editors.connections.delete_connection(key)
    if outside is None:
        svc.revert(res.run.id, res.change.id)
        refs = {
            e.properties.get("wiki_prior_ref")
            for e in stack.graph.get_edges("w")
            if e.type == "CONNECTED_TO"
        }
        assert refs == {"gone-prior"}
        return
    before = stack.state()
    with pytest.raises(RevertConflictError):
        svc.revert(res.run.id, res.change.id)
    assert stack.state() == before


def test_concurrent_reverts_of_one_change_take_turns() -> None:
    """NFR N3-7: two clicks on one undo -> one revert, one 409."""
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    res = svc.answer(
        run.id,
        AugmentationAnswer(
            question_id=_question(run, "low_confidence", w["ghost"].id).id, action="confirm"
        ),
    )
    engine = svc._engine
    original = engine.revert

    def slow(world_id, change):
        time.sleep(0.05)
        original(world_id, change)

    engine.revert = slow  # type: ignore[method-assign]
    outcomes: list[str] = []
    barrier = threading.Barrier(2)

    def click() -> None:
        barrier.wait()
        try:
            svc.revert(run.id, res.change.id)  # type: ignore[union-attr]
            outcomes.append("ok")
        except ChangeAlreadyRevertedError:
            outcomes.append("409")

    threads = [threading.Thread(target=click) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(outcomes) == ["409", "ok"]


# --------------------------------------------------------------------------- #
# TP-U3-4: any answers, then undo latest first, give back the start
# --------------------------------------------------------------------------- #
def _answer_for(stack: Stack, q, pick: int) -> AugmentationAnswer:
    snap = stack.cache.get("w")
    actions = [a for a in q.actions if a != AnswerAction.IGNORE]
    action = actions[pick % len(actions)]
    regions = [r.id for r in snap.topo.regions]
    refs = {
        "parent_id": regions,
        "located_in": regions,
        "wiki_prior_ref": [p.id for p in snap.kg.priors],
        "derived_from_prior_ids": [p.id for p in snap.kg.priors],
        "about_entity_ids": [e.id for e in snap.kg.entities],
    }.get(q.target.field or "", [])
    if action == AnswerAction.EDIT and q.target.field and not refs:
        action = AnswerAction.REMOVE
    return AugmentationAnswer(
        question_id=q.id,
        action=action,
        statement=f"s{pick}",
        region_id=regions[pick % len(regions)] if regions else None,
        ref_id=refs[pick % len(refs)] if refs else None,
    )


@_PBT
@given(
    file=editable_worlds(),
    picks=st.lists(
        st.tuples(st.integers(0, 50), st.integers(0, 50), st.booleans()), min_size=1, max_size=5
    ),
)
def test_tp_u3_4_answers_then_undo_restore_the_world(file: WorldFile, picks) -> None:
    stack = Stack(file)
    initial = stack.state()
    svc = _service(stack)
    run = svc.start_run("w")
    for qi, pick, ignore in picks:
        if run.status != RunStatus.OPEN or not run.open_questions:
            break
        q = run.open_questions[qi % len(run.open_questions)]
        answer = (
            AugmentationAnswer(question_id=q.id, action="ignore")
            if ignore
            else _answer_for(stack, q, pick)
        )
        try:
            run = svc.answer(run.id, answer).run
        except (ValueError, LookupError):  # refused before any write (a cycle, a bad ref)
            assert stack.cache.get("w") is not None
    live = [c for c in run.history if not c.reverted]
    if len(live) >= 2:
        with pytest.raises(RevertOrderError):
            svc.revert(run.id, live[0].id)
    for change in reversed(live):
        svc.revert(run.id, change.id)
    assert stack.state() == initial


# --------------------------------------------------------------------------- #
# LLM use: caches, caps, budget (BR-U3-41, NFR R-03)
# --------------------------------------------------------------------------- #
class _LLM:
    def __init__(self, conflicts: bool = True) -> None:
        self.calls: list[str] = []
        self._conflicts = conflicts

    def structured(self, prompt, schema, *, system=None):
        self.calls.append(schema.__name__)
        if schema.__name__ == "_Verdict":
            return schema(conflicts=self._conflicts, reason="rivers do not flow uphill\nX")
        return schema(text="Could you check this?")


class _Wiki:
    def __init__(self, hits: bool = True) -> None:
        self.calls: list[tuple[str, bool]] = []
        self._hits = hits

    def lookup_similar(self, query, k=5, *, fallback=True):
        self.calls.append((query, fallback))
        if not self._hits:
            return []
        return [
            WikiPrior(
                world_id="w",
                prior_type=PriorType.FACT,
                condition="river",
                effect="water flows downhill",
                provenance=_prov(),
            )
        ]


def _llm_service(stack: Stack, llm, wiki, **kw) -> AugmentationService:
    return _service(stack, engine={"llm": llm, "wiki_provider": lambda wid: wiki}, **kw)


def test_wiki_conflict_reads_terrain_kind_and_never_asks_for_a_fallback() -> None:
    stack, w = _seeded()
    llm, wiki = _LLM(), _Wiki()
    run = _llm_service(stack, llm, wiki).start_run("w")
    conflict = _question(run, "wiki_conflict", w["fish"].id)
    assert conflict.target is not None and conflict.target.region_name == "Riverton"
    assert wiki.calls == [("river Riverton", False)]  # search only (NFR R-03)
    issue = next(i for i in run.issues if i.id == conflict.issue_id)
    assert "\n" not in issue.description  # the reason is one line


def test_same_snapshot_detected_again_calls_no_llm_and_an_edit_rejudges_once() -> None:
    stack, w = _seeded()
    llm, wiki = _LLM(), _Wiki()
    engine = AugmentationEngine(stack.editors, llm=llm, wiki_provider=lambda wid: wiki)
    state = RunState(run=AugmentationRun(world_id="w"))
    for _ in range(5):  # polish is 5 new questions per detection; later ones catch up
        issues, snap = engine.detect("w", state, lambda: True)
        engine.questions(issues, snap, state, lambda: True)
    assert llm.calls.count("_Verdict") == 1
    used = len(llm.calls)
    issues, snap = engine.detect("w", state, lambda: True)
    engine.questions(issues, snap, state, lambda: True)
    assert len(llm.calls) == used  # cached verdicts and polished text: no call
    fish = gm.node_to_knowledge(stack.graph.get_node("w", w["fish"].id))  # type: ignore[arg-type]
    stack.editors.knowledge.upsert_knowledge(fish.model_copy(update={"statement": "eels"}))
    engine.detect("w", state, lambda: True)
    assert llm.calls[used:] == ["_Verdict"]  # only the edited item is judged again


def test_a_spent_budget_keeps_the_cached_conflicts_after_an_edit() -> None:
    """U3 review #9: once the budget is spent an edited item is not judged again, and
    the cached verdicts of the items sorted after it still make wiki_conflict issues."""
    stack, w = _seeded()
    for kid in ("k-a", "k-b"):
        stack.editors.knowledge.create_knowledge(
            Knowledge(
                id=kid, world_id="w", statement=f"{kid} flows uphill", title=kid, provenance=_prov()
            ),
            w["riverton"].id,
        )
    llm, wiki = _LLM(), _Wiki()
    engine = AugmentationEngine(stack.editors, llm=llm, wiki_provider=lambda wid: wiki)
    state = RunState(run=AugmentationRun(world_id="w"))
    issues, _snap = engine.detect("w", state, lambda: True)
    conflicts = {i.target_ids[0] for i in issues if i.type == IssueType.WIKI_CONFLICT}
    assert {"k-a", "k-b"} <= conflicts
    ka = gm.node_to_knowledge(stack.graph.get_node("w", "k-a"))  # type: ignore[arg-type]
    stack.editors.knowledge.upsert_knowledge(ka.model_copy(update={"statement": "k-a, edited"}))
    issues, _snap = engine.detect("w", state, lambda: False)  # the budget is spent
    conflicts = {i.target_ids[0] for i in issues if i.type == IssueType.WIKI_CONFLICT}
    assert "k-b" in conflicts and "k-a" not in conflicts


def test_no_grounding_prior_means_no_judgement() -> None:
    stack, _w = _seeded()
    llm = _LLM()
    _llm_service(stack, llm, _Wiki(hits=False)).start_run("w")
    assert "_Verdict" not in llm.calls


def test_polish_is_capped_per_detection_and_the_run_budget_holds() -> None:
    stack, _w = _seeded()
    for i in range(10):  # ten more empty regions -> ten more gap questions
        stack.editors.regions.create_region(
            Region(world_id="w", name=f"R{i}", level=RegionLevel.TOWN, provenance=_prov())
        )
    llm = _LLM(conflicts=False)
    run = _llm_service(stack, llm, _Wiki()).start_run("w")
    assert llm.calls.count("_Polished") == 5  # POLISH_MAX new questions per detection
    assert run.llm_calls == len(llm.calls)
    tight = _llm_service(stack, _LLM(conflicts=False), _Wiki(), llm_budget=3)
    run = tight.start_run("w")
    assert run.llm_calls == 3 and run.llm_budget_exhausted
    run = tight.answer(
        run.id, AugmentationAnswer(question_id=run.open_questions[0].id, action="ignore")
    ).run
    assert run.llm_calls == 3  # nothing past the budget


def test_a_run_without_an_llm_uses_templates() -> None:
    stack, _w = _seeded()
    run = _service(stack).start_run("w")
    assert run.llm_calls == 0 and run.open_questions
    assert IssueType.WIKI_CONFLICT.value not in {str(i.type) for i in run.issues}


# --------------------------------------------------------------------------- #
# store and cache
# --------------------------------------------------------------------------- #
def test_run_store_roundtrip() -> None:
    # U3 intended change: BR-U3-42 — the store keeps run state (caches, lock), 20 per world
    store = InMemoryRunStore(per_world=2)
    states = [RunState(run=AugmentationRun(world_id="w")) for _ in range(3)]
    for s in states:
        store.save(s)
    assert store.get(states[0].run.id) is None  # the oldest of the world went
    assert store.get(states[2].run.id) is states[2]
    other = RunState(run=AugmentationRun(world_id="v"))
    store.save(other)
    assert store.get(states[1].run.id) is states[1]  # another world does not evict
    assert store.get("missing") is None


def test_service_loop_converges() -> None:
    # U3 intended change: C-3 — a real engine over a world; the answer returns AnswerResult
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    assert run.status == RunStatus.OPEN and run.open_questions
    q = _question(run, "gap", w["hollow"].id)
    res = svc.answer(run.id, AugmentationAnswer(question_id=q.id, action="add", statement="x"))
    assert res.change in res.run.history and res.run.answers == 1
    assert all(q.target.id != w["hollow"].id for q in res.run.open_questions if q.target)


def test_engine_apply_and_revert_invalidate_cache() -> None:
    # U3 intended change: the editor classes invalidate (the engine holds no cache)
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    gen = stack.cache.generation("w")
    res = svc.answer(
        run.id,
        AugmentationAnswer(
            question_id=_question(run, "low_confidence", w["fish"].id).id, action="confirm"
        ),
    )
    assert stack.cache.generation("w") > gen
    gen = stack.cache.generation("w")
    svc.revert(run.id, res.change.id)  # type: ignore[union-attr]
    assert stack.cache.generation("w") > gen
