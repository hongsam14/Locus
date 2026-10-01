"""U3 code-review-01 items closed in U8 Step 9b (augmentation Q&A).

C2 the question says its type, inputs and reference kind · C10 edges read around the
target · S03 an interrupted undo resumes · S09 a failed wiki search is tried again ·
S15 a failed re-detection cannot apply an answer twice.
"""

from __future__ import annotations

import pytest

from locus.shared.models import ConnectionEdge, ConnectionKind, WikiPrior
from locus.world.augmentation import AugmentationEngine, RunState
from locus.world.augmentation.types import AugmentationAnswer, AugmentationRun
from tests.world.augmentation.test_augmentation import (
    _LLM,
    _prov,
    _question,
    _seeded,
    _service,
)


def test_c2_a_question_carries_its_type_inputs_and_reference_kind() -> None:
    stack, w = _seeded()
    run = _service(stack).start_run("w")
    gap = _question(run, "gap", w["hollow"].id)
    assert gap.type == "gap" and gap.needs == {"add": ["statement", "title"]}
    low = _question(run, "low_confidence", w["fish"].id)
    assert low.needs == {"edit": ["statement", "title", "confidence"]}  # S06 inputs
    dangling = _question(run, "dangling", w["tomas"].id)
    assert dangling.ref_kind == "region" and dangling.needs == {"edit": ["ref"]}


def test_c2_a_connection_target_is_a_key_and_an_added_fact_is_named_by_its_title() -> None:
    stack, w = _seeded()
    edge = ConnectionEdge(
        world_id="w",
        source_region_id=w["riverton"].id,
        target_region_id=w["hollow"].id,
        kind=ConnectionKind.ROUTE,
        weight=0.5,
        wiki_prior_ref="gone-prior",
        provenance=_prov(),
    )
    stack.editors.connections.upsert_connection(edge)
    svc = _service(stack)
    run = svc.start_run("w")
    q = next(q for q in run.open_questions if q.target and q.target.kind == "connection")
    assert q.target.connection is not None and q.target.connection.kind == "route"
    assert q.ref_kind == "prior"
    gap = _question(run, "gap", w["hollow"].id)
    res = svc.answer(
        run.id,
        AugmentationAnswer(question_id=gap.id, action="add", statement="The well ran dry"),
    )
    assert [c.name for c in res.changed if c.id in res.change.added_ids] == ["The well ran dry"]


def test_c10_an_answer_reads_only_the_edges_around_its_target() -> None:
    stack, w = _seeded()
    reads: list[str] = []
    real = stack.graph.get_edges
    stack.graph.get_edges = lambda *a, **k: (reads.append("get_edges"), real(*a, **k))[1]
    svc = _service(stack)
    run = svc.start_run("w")
    reads.clear()
    q = _question(run, "low_confidence", w["fish"].id)
    svc._engine.apply(
        "w",
        run.issues[[i.id for i in run.issues].index(q.issue_id)],
        q,
        AugmentationAnswer(question_id=q.id, action="confirm"),
    )
    assert reads == []  # no whole-world edge scan for the change record


def test_s03_an_undo_cut_after_its_graph_writes_finishes_on_the_retry() -> None:
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    gap = _question(run, "gap", w["hollow"].id)
    res = svc.answer(
        run.id, AugmentationAnswer(question_id=gap.id, action="add", statement="Wells run dry")
    )
    added = res.change.added_ids[0]
    stack.meter.calls.clear()
    real_index = stack.search.index
    calls = {"n": 0}

    def failing_index(docs):  # the graph is already back when the search write fails
        calls["n"] += 1
        raise RuntimeError("search down")

    stack.search.index = failing_index
    stack.search.delete = lambda world_id, ids: (_ for _ in ()).throw(RuntimeError("down"))
    with pytest.raises(RuntimeError):
        svc.revert(run.id, res.change.id)
    assert stack.graph.get_node("w", added) is None
    stack.search.index = real_index
    del stack.search.delete  # back to the class method
    again = svc.revert(run.id, res.change.id)  # was 409 "edited after this change"
    assert next(c for c in again.history if c.id == res.change.id).reverted


def test_s09_a_failed_wiki_search_is_tried_again() -> None:
    stack, _w = _seeded()

    class _FlakyWiki:
        def __init__(self) -> None:
            self.calls = 0

        def lookup_similar(self, query, k=5, *, fallback=True):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("search timed out")
            return [
                WikiPrior(
                    world_id="w",
                    prior_type="fact",
                    condition="river",
                    effect="water flows downhill",
                    provenance=_prov(),
                )
            ]

    wiki, llm = _FlakyWiki(), _LLM()
    engine = AugmentationEngine(stack.editors, llm=llm, wiki_provider=lambda wid: wiki)
    state = RunState(run=AugmentationRun(world_id="w"))
    engine.detect("w", state, lambda: True)
    assert "_Verdict" not in llm.calls
    engine.detect("w", state, lambda: True)
    assert wiki.calls == 2 and "_Verdict" in llm.calls


def test_s15_a_failed_redetection_cannot_apply_the_same_answer_twice() -> None:
    stack, w = _seeded()
    svc = _service(stack)
    run = svc.start_run("w")
    gap = _question(run, "gap", w["hollow"].id)
    real_detect = svc._engine.detect

    def broken(*a, **k):
        raise RuntimeError("graph read failed")

    svc._engine.detect = broken  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        svc.answer(run.id, AugmentationAnswer(question_id=gap.id, action="add", statement="x"))
    svc._engine.detect = real_detect  # type: ignore[method-assign]
    with pytest.raises(LookupError, match="question not found"):
        svc.answer(run.id, AugmentationAnswer(question_id=gap.id, action="add", statement="x"))
    added = [k for k in stack.cache.get("w").kg.knowledge if k.statement == "x"]
    assert len(added) == 1


def test_s10_removing_or_undoing_knowledge_purges_its_translations(monkeypatch) -> None:
    """U3 review S10 (BR-U3-3): every path that deletes knowledge purges its
    translations — the Q&A REMOVE answer and the undo of an added fact."""
    from fastapi.testclient import TestClient

    import api.routers.world as world_router
    from api.main import create_app
    from locus.world.wiring import WorldContainer

    stack, w = _seeded()
    purged: list[list[str]] = []
    monkeypatch.setattr(
        world_router, "purge_translations", lambda loc, *, kind, ids: purged.append(list(ids))
    )
    world = WorldContainer(
        cache=stack.cache,
        editors=stack.editors,
        exporter=None,
        importer=None,
        demo=None,
        augmentation=_service(stack),
    )
    client = TestClient(create_app(world=world))
    run = client.post("/api/world/worlds/w/augmentation/runs").json()
    low = next(q for q in run["open_questions"] if q["target"]["id"] == w["fish"].id)
    client.post(
        f"/api/world/augmentation/runs/{run['id']}/answer",
        json={"question_id": low["id"], "action": "remove"},
    )
    assert purged == [[w["fish"].id]]
    run = client.get(f"/api/world/augmentation/runs/{run['id']}").json()
    gap = next(q for q in run["open_questions"] if q["issue_key"].startswith("gap:"))
    res = client.post(
        f"/api/world/augmentation/runs/{run['id']}/answer",
        json={"question_id": gap["id"], "action": "add", "statement": "A dry well"},
    ).json()
    added = res["change"]["added_ids"]
    client.post(
        f"/api/world/augmentation/runs/{run['id']}/revert",
        params={"change_id": res["change"]["id"]},
    )
    assert purged[-1] == added


# --------------------------------------------------------------------------- #
# U8 code-review-01 #6: a revert cut between its graph writes is finished by the retry
# --------------------------------------------------------------------------- #
def _answered(case: str):
    stack, w = _seeded()
    svc = _service(stack)
    if case == "connection_remove":
        stack.editors.connections.upsert_connection(
            ConnectionEdge(
                world_id="w",
                source_region_id=w["riverton"].id,
                target_region_id=w["hollow"].id,
                kind=ConnectionKind.ROUTE,
                weight=0.5,
                rationale="old road",
                wiki_prior_ref="gone-prior",
                provenance=_prov(),
            )
        )
    run = svc.start_run("w")
    if case == "gap_add":
        q = _question(run, "gap", w["hollow"].id)
        answer = AugmentationAnswer(question_id=q.id, action="add", statement="Wells run dry")
    elif case == "confirm":
        q = _question(run, "low_confidence", w["fish"].id)
        answer = AugmentationAnswer(question_id=q.id, action="confirm")
    else:
        q = next(q for q in run.open_questions if q.target and q.target.kind == "connection")
        answer = AugmentationAnswer(question_id=q.id, action="remove")
    state = stack.state()  # what a finished revert must give back
    res = svc.answer(run.id, answer)
    assert res.change is not None
    return stack, svc, run.id, res.change.id, state


@pytest.mark.parametrize("case", ["gap_add", "confirm", "connection_remove"])
def test_u8_6_a_revert_cut_at_any_write_is_finished_by_the_retry(case) -> None:
    stack, svc, run_id, change_id, state = _answered(case)
    start = len(stack.meter.calls)
    svc.revert(run_id, change_id)
    writes = len(stack.meter.calls) - start
    assert stack.state() == state and writes > 1
    for n in range(writes):
        stack, svc, run_id, change_id, state = _answered(case)
        stack.meter.cut_at = len(stack.meter.calls) + n
        with pytest.raises(RuntimeError, match="cut at write"):
            svc.revert(run_id, change_id)
        again = svc.revert(run_id, change_id)  # was a lasting 409 "edited after"
        assert stack.state() == state, f"{case}: cut at write {n}"
        assert next(c for c in again.history if c.id == change_id).reverted


def test_u8_6_an_outside_edit_still_blocks_a_resumed_revert() -> None:
    """Resuming is lenient only about the revert's own half-done writes."""
    stack, svc, run_id, change_id, _state = _answered("connection_remove")
    stack.meter.cut_at = len(stack.meter.calls)  # cut at the first write
    with pytest.raises(RuntimeError, match="cut at write"):
        svc.revert(run_id, change_id)
    pairs = [e for e in stack.graph.get_edges("w", ["CONNECTED_TO"]) if e.properties.get("kind")]
    outside = pairs[0].model_copy(update={"properties": {**pairs[0].properties, "weight": 0.95}})
    stack.graph.upsert_edges([outside])  # the designer saved a new weight meanwhile
    stack.cache.invalidate("w")
    with pytest.raises(Exception, match="edited after"):
        svc.revert(run_id, change_id)
