"""Shared fakes for the play / gm API tests: in-memory play container over a tiny world."""

from __future__ import annotations

from locus.play import InMemoryPlayRepository
from locus.play.event.suggester import EventDraft, EventDraftList, EventSuggester
from locus.play.models import EventCategory
from locus.play.rumor.generator import RumorDraft, RumorGenerator
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import PlayContainer
from locus.shared.models import (
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    ScopeType,
    SourceKind,
)
from locus.shared.storage.base import Node
from tests.play.helpers import compose_play
from tests.shared.snapshots import snapshot_of


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class GraphRepo:
    def find_nodes(self, world_id, label, filters=None):
        if label == "Region" and world_id == "w":
            return [Node(id="r1", label="Region", world_id=world_id, properties={"id": "r1"})]
        return []


class RumorLLM:
    """structured() drives rumor generation; complete() drives translation ('KO:'+text)."""

    def structured(self, prompt, schema, *, system=None):
        return RumorDraft(statement="distorted")

    def complete(self, prompt, *, system=None):
        return "KO:" + prompt.split("Text:\n", 1)[-1]


class SuggestLLM:
    def structured(self, prompt, schema, *, system=None):
        return EventDraftList(
            drafts=[EventDraft(region_id="r1", category=EventCategory.WAR, magnitude=0.5)]
        )

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


class Loader:
    def __init__(self) -> None:
        self.region = Region(world_id="w", name="R1", level=RegionLevel.TOWN, provenance=_prov())
        self.region.id = "r1"  # match the graph repo region id
        k = Knowledge(world_id="w", statement="fact", title="t", provenance=_prov())
        scope = ScopeLink(
            world_id="w", knowledge_id=k.id, region_id="r1", scope_type=ScopeType.DIRECT
        )
        self._kg = KnowledgeGraph(world_id="w", knowledge=[k], scopes=[scope])
        self._topo = RegionTopology(world_id="w", regions=[self.region])

    def get(self, world_id):
        if world_id != "w":  # mirrors WorldCache: unknown / empty world -> LookupError
            raise LookupError(f"world not found: {world_id}")
        return snapshot_of(self._kg, self._topo)


class DialogueLLM:
    """NPC answers for the API tests: records each call, answers in a fixed voice."""

    def __init__(self, answer: str = "They say the river rose again.") -> None:
        self.answer = answer
        self.calls: list[tuple[str, str | None]] = []

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        raise AssertionError("dialogue never uses structured output")

    def complete(self, prompt, *, system=None):
        self.calls.append((prompt, system))
        return self.answer


def play_container(
    *, with_suggester: bool = False, executor=None, dialogue_llm=None
) -> PlayContainer:
    repo = InMemoryPlayRepository()
    loader = Loader()
    suggester = EventSuggester(SuggestLLM()) if with_suggester else None
    return compose_play(
        repo,
        RumorGenerator(RumorLLM()),
        loader,
        suggester=suggester,
        executor=executor or SyncTurnExecutor(),
        dialogue_llm=dialogue_llm if dialogue_llm is not None else DialogueLLM(),
    )
