"""U7 Augmentation tests — detectors, questions, apply/revert, service loop (mocked)."""

from __future__ import annotations

from locus.augmentation import (
    AugmentationService,
    InMemorySessionStore,
)
from locus.augmentation.apply import apply_answer
from locus.augmentation.apply import revert as apply_revert
from locus.augmentation.detectors import detect_gaps, detect_low_confidence
from locus.augmentation.questions import QuestionGenerator
from locus.augmentation.types import (
    AnswerAction,
    AugmentationAnswer,
    AugmentationQuestion,
    AugmentationSession,
    ChangeSet,
    Issue,
    IssueType,
    SessionStatus,
)
from locus.models import (
    Entity,
    EntityType,
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    Relation,
    SourceKind,
)
from locus.storage import graph_mapping as gm
from locus.storage.base import Node


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


# --------------------------------------------------------------------------- #
# detectors (pure)
# --------------------------------------------------------------------------- #
def test_detect_gaps_empty_region_and_dangling() -> None:
    a = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=_prov())
    k = Knowledge(world_id="w", statement="x", provenance=_prov())
    rel = Relation(
        world_id="w",
        source_id="missing",
        target_id="also-missing",
        relation_type="knows",
        provenance=_prov(),
    )
    kg = KnowledgeGraph(world_id="w", knowledge=[k], relations=[rel])  # no scopes -> A is empty
    topo = RegionTopology(world_id="w", regions=[a])
    issues = detect_gaps(kg, topo)
    types = {str(i.type) for i in issues}
    assert IssueType.GAP.value in types
    assert IssueType.DANGLING.value in types


def test_detect_low_confidence() -> None:
    k = Knowledge(world_id="w", statement="maybe", confidence=0.3, provenance=_prov())
    e = Entity(
        world_id="w", name="E", entity_type=EntityType.PLACE, confidence=0.2, provenance=_prov()
    )
    kg = KnowledgeGraph(world_id="w", knowledge=[k], entities=[e])
    issues = detect_low_confidence(kg)
    assert len(issues) == 2
    assert all(str(i.type) == IssueType.LOW_CONFIDENCE.value for i in issues)


def test_question_generator_template() -> None:
    issue = Issue(type=IssueType.LOW_CONFIDENCE, description="low conf item")
    q = QuestionGenerator(llm=None).generate(issue)
    assert q.issue_id == issue.id
    assert q.options  # template options present


# --------------------------------------------------------------------------- #
# apply / revert
# --------------------------------------------------------------------------- #
class _Editor:
    def __init__(self) -> None:
        self.upserted: list = []
        self.deleted: list = []

    def upsert_knowledge(self, knowledge):
        self.upserted.append(knowledge)
        return knowledge

    def delete_node(self, world_id, node_id):
        self.deleted.append(node_id)


class _GraphRepo:
    def __init__(self, node: Node | None = None) -> None:
        self._node = node
        self.edges: list = []
        self.nodes: list = []

    def get_node(self, world_id, node_id):
        return self._node

    def upsert_edges(self, edges):
        self.edges.extend(edges)

    def upsert_nodes(self, nodes):
        self.nodes.extend(nodes)


def test_apply_add_creates_knowledge_and_scope() -> None:
    editor, graph = _Editor(), _GraphRepo()
    answer = AugmentationAnswer(
        question_id="q1", action=AnswerAction.ADD, statement="new lore", region_id="r1"
    )
    cs = apply_answer(answer, world_id="w", graph_repo=graph, editor=editor)
    assert len(cs.added_ids) == 1
    assert editor.upserted[0].statement == "new lore"
    assert editor.upserted[0].provenance.source == SourceKind.AUGMENTATION
    assert any(e.type == "SCOPED_TO" for e in graph.edges)


def test_apply_remove_and_revert() -> None:
    k = Knowledge(world_id="w", statement="bad", provenance=_prov())
    node = gm.knowledge_to_node(k)
    editor, graph = _Editor(), _GraphRepo(node=node)
    answer = AugmentationAnswer(question_id="q1", action=AnswerAction.REMOVE, target_id=k.id)
    cs = apply_answer(answer, world_id="w", graph_repo=graph, editor=editor)
    assert editor.deleted == [k.id]
    assert cs.removed and cs.removed[0].id == k.id
    # revert restores the removed node
    apply_revert(cs, world_id="w", graph_repo=graph, editor=editor)
    assert graph.nodes and graph.nodes[0].id == k.id


# --------------------------------------------------------------------------- #
# session store + service loop
# --------------------------------------------------------------------------- #
class _StubEngine:
    """Yields one issue on the first detect, none afterwards."""

    def __init__(self) -> None:
        self.calls = 0

    def detect_issues(self, world_id):
        self.calls += 1
        return [Issue(type=IssueType.GAP, description="gap")] if self.calls == 1 else []

    def generate_questions(self, issues):
        return [AugmentationQuestion(issue_id=i.id, text="q?", options=["add"]) for i in issues]

    def apply_answer(self, world_id, answer):
        return ChangeSet(description="applied")

    def revert(self, world_id, change):
        self.reverted = change.id


def test_session_store_roundtrip() -> None:
    store = InMemorySessionStore()
    sess = AugmentationSession(world_id="w")
    store.save(sess)
    assert store.get(sess.id) is sess
    store.delete(sess.id)
    assert store.get(sess.id) is None


def test_service_loop_converges() -> None:
    svc = AugmentationService(_StubEngine(), InMemorySessionStore(), max_rounds=5)
    session = svc.start_session("w")
    assert session.status == SessionStatus.OPEN
    assert len(session.open_questions) == 1

    answer = AugmentationAnswer(question_id=session.open_questions[0].id, action=AnswerAction.ADD)
    change = svc.submit_answer(session.id, answer)
    after = svc.get_session(session.id)
    assert after.status == SessionStatus.CONVERGED  # second detect returns no issues
    assert change in after.history
    # revert is delegated to the engine
    svc.revert(session.id, change.id)
