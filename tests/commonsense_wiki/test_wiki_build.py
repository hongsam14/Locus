"""Wiki tests — graph_mapping, distiller(+domains), linker, cross-world, admin (mocked)."""

from __future__ import annotations

from locus.commonsense_wiki import (
    CrossWorldWikiExplorer,
    PriorDistiller,
    WikiAdmin,
    WikiPriorLinker,
)
from locus.commonsense_wiki.schemas import PriorBatch, PriorLinkVerdict, PriorSuggestion
from locus.models import (
    ConnectionEdge,
    ConnectionKind,
    IngestionResult,
    Knowledge,
    PriorType,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    SearchHit,
    SourceKind,
    WikiDomain,
    WikiPrior,
    WikiPriorLink,
)
from locus.storage import graph_mapping as gm


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _prior(world_id="w", domains=None, condition="mountain", effect="slow") -> WikiPrior:
    return WikiPrior(
        world_id=world_id,
        prior_type=PriorType.TERRAIN_RULE,
        condition=condition,
        effect=effect,
        domains=domains or [WikiDomain.GEOGRAPHY],
        provenance=_prov(),
    )


# --------------------------------------------------------------------------- #
# graph_mapping (pure)
# --------------------------------------------------------------------------- #
def test_region_node_flattens_provenance_and_attributes() -> None:
    r = Region(
        world_id="w",
        name="T",
        level=RegionLevel.TOWN,
        attributes={"terrain": "river"},
        provenance=_prov(),
    )
    node = gm.region_to_node(r)
    assert node.label == "Region"
    assert node.properties["prov_source"] == "input"
    assert isinstance(node.properties["attributes"], str)
    assert "provenance" not in node.properties


def test_contains_and_scope_edges() -> None:
    parent = Region(world_id="w", name="P", level=RegionLevel.PROVINCE, provenance=_prov())
    child = Region(
        world_id="w", name="C", level=RegionLevel.TOWN, parent_id=parent.id, provenance=_prov()
    )
    edges = gm.contains_edges([parent, child])
    assert edges[0].type == "CONTAINS"
    assert edges[0].source_id == parent.id and edges[0].target_id == child.id

    s = ScopeLink(world_id="w", knowledge_id="k1", region_id=child.id, confidence=0.9)
    se = gm.scope_edges([s])[0]
    assert se.type == "SCOPED_TO" and se.properties["confidence"] == 0.9


def test_knowledge_node_and_doc_carry_title() -> None:
    k = Knowledge(
        world_id="w", statement="rivers enable trade", title="River trade", provenance=_prov()
    )
    node = gm.knowledge_to_node(k)
    assert node.properties["title"] == "River trade"
    back = gm.node_to_knowledge(node)
    assert back.title == "River trade"
    doc = gm.knowledge_doc(k)
    assert "River trade" in doc.text  # BR-A3
    assert doc.meta["title"] == "River trade"


def test_wikiprior_node_doc_roundtrip_with_domains_and_world() -> None:
    p = _prior(world_id="w2", domains=[WikiDomain.GEOGRAPHY, WikiDomain.LOGISTICS])
    node = gm.wikiprior_to_node(p)
    assert node.world_id == "w2"
    back = gm.node_to_wikiprior(node)
    assert back.world_id == "w2"
    assert {str(d) for d in back.domains} == {"geography", "logistics"}
    doc = gm.wikiprior_doc(p)
    assert doc.world_id == "w2"
    assert "logistics" in doc.meta["domains"]


def test_prior_link_edge_roundtrip() -> None:
    link = WikiPriorLink(
        world_id="w",
        source_id="a",
        target_id="b",
        relation="reinforces",
        weight=0.7,
        cross_domain=True,
        provenance=_prov(),
    )
    edge = gm.prior_link_edges([link])[0]
    assert edge.type == "PRIOR_RELATED_TO"
    assert edge.properties["relation"] == "reinforces"
    assert edge.properties["cross_domain"] is True
    back = gm.edge_to_prior_link(edge)
    assert back.weight == 0.7 and back.source_id == "a"


def test_located_in_edges() -> None:
    from locus.models import Entity, EntityType

    e = Entity(
        world_id="w",
        name="Tower",
        entity_type=EntityType.PLACE,
        located_in="r1",
        provenance=_prov(),
    )
    orphan = Entity(
        world_id="w", name="Floating", entity_type=EntityType.OBJECT, provenance=_prov()
    )
    edges = gm.located_in_edges([e, orphan])
    assert len(edges) == 1  # only the entity with located_in (BR-B5)
    assert edges[0].type == "LOCATED_IN"
    assert edges[0].source_id == e.id and edges[0].target_id == "r1"


def test_connection_edges_count() -> None:
    c = ConnectionEdge(
        world_id="w",
        source_region_id="a",
        target_region_id="b",
        kind=ConnectionKind.ROUTE,
        weight=0.6,
        provenance=_prov(),
    )
    assert gm.connection_edges([c])[0].properties["weight"] == 0.6


# --------------------------------------------------------------------------- #
# PriorDistiller (now per-world + domains)
# --------------------------------------------------------------------------- #
class _FakeLLM:
    def __init__(self, batch: PriorBatch) -> None:
        self._batch = batch

    def structured(self, prompt, schema, *, system=None):
        return self._batch


def test_distiller_sets_world_id_and_domains() -> None:
    batch = PriorBatch(
        items=[
            PriorSuggestion(
                prior_type=PriorType.TERRAIN_RULE,
                condition="mountain",
                effect="slow",
                domains=[WikiDomain.GEOGRAPHY],
                confidence=0.9,
            ),
            PriorSuggestion(condition="", effect="x"),  # invalid -> dropped
            PriorSuggestion(condition="sea", effect="trade"),  # no domains -> [OTHER]
        ]
    )
    priors = PriorDistiller(_FakeLLM(batch)).distill(
        IngestionResult(world_id="w"), RegionTopology(world_id="w"), world_id="w"
    )
    assert len(priors) == 2
    assert priors[0].world_id == "w"
    assert priors[0].domains == [WikiDomain.GEOGRAPHY]
    assert priors[1].domains == [WikiDomain.OTHER]  # BR-A5


def test_distiller_graceful_on_error() -> None:
    class _Boom:
        def structured(self, *a, **k):
            raise RuntimeError("x")

    assert (
        PriorDistiller(_Boom()).distill(
            IngestionResult(world_id="w"), RegionTopology(world_id="w"), world_id="w"
        )
        == []
    )


# --------------------------------------------------------------------------- #
# WikiPriorLinker
# --------------------------------------------------------------------------- #
class _FakeEmbed:
    def __init__(self, vectors: dict[str, list[float]]) -> None:
        self._v = vectors

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._v.get(t.split()[0], [0.0, 0.0]) for t in texts]


class _LinkLLM:
    def __init__(self, verdict: PriorLinkVerdict) -> None:
        self._verdict = verdict
        self.calls = 0

    def structured(self, prompt, schema, *, system=None):
        self.calls += 1
        return self._verdict


def test_linker_creates_links_with_embedding_gate() -> None:
    a = _prior(domains=[WikiDomain.GEOGRAPHY], condition="alpha mountain", effect="x")
    b = _prior(domains=[WikiDomain.ECONOMY], condition="beta trade", effect="y")
    embed = _FakeEmbed({"alpha": [1.0, 0.0], "beta": [0.9, 0.1]})
    llm = _LinkLLM(PriorLinkVerdict(related=True, relation="affects", weight=0.6))
    links = WikiPriorLinker(llm, embed, top_k=2).link([a, b], world_id="w")
    assert len(links) == 1
    assert links[0].relation == "affects"
    assert links[0].cross_domain is True  # geography vs economy
    assert links[0].world_id == "w"


def test_linker_drops_low_weight_and_handles_no_embedding() -> None:
    a, b = _prior(condition="a x"), _prior(condition="b y")
    llm = _LinkLLM(PriorLinkVerdict(related=True, relation="r", weight=0.1))  # below threshold
    embed = _FakeEmbed({"a": [1.0, 0.0], "b": [1.0, 0.0]})
    assert WikiPriorLinker(llm, embed).link([a, b], world_id="w") == []
    # no embedding provider -> graceful empty
    assert WikiPriorLinker(llm, None).link([a, b], world_id="w") == []


# --------------------------------------------------------------------------- #
# CrossWorldWikiExplorer (designer-only)
# --------------------------------------------------------------------------- #
class _GraphWithPriors:
    def __init__(self, by_world: dict[str, list[WikiPrior]]) -> None:
        self._by_world = by_world

    def find_nodes(self, world_id, label, filters=None):
        return [gm.wikiprior_to_node(p) for p in self._by_world.get(world_id, [])]


class _GlobalSearch:
    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits
        self.calls: list[dict] = []

    def hybrid_search(self, world_id, query_text, query_embedding=None, k=5, filters=None):
        self.calls.append({"world_id": world_id, "filters": filters})
        return self._hits


def test_cross_world_world_domains_aggregates() -> None:
    g = _GraphWithPriors(
        {"w1": [_prior(domains=[WikiDomain.GEOGRAPHY]), _prior(domains=[WikiDomain.CLIMATE])]}
    )
    explorer = CrossWorldWikiExplorer(g, _GlobalSearch([]))
    assert explorer.world_domains("w1") == {WikiDomain.GEOGRAPHY, WikiDomain.CLIMATE}


def test_cross_world_search_excludes_own_world_global_query() -> None:
    g = _GraphWithPriors({"w1": [_prior(world_id="w1", domains=[WikiDomain.GEOGRAPHY])]})
    other = SearchHit(
        id="p_other",
        world_id="w2",
        label="WikiPrior",
        text="desert isolates",
        score=1.0,
        meta={
            "prior_type": "fact",
            "condition": "desert",
            "effect": "isolation",
            "domains": ["geography"],
        },
    )
    own = SearchHit(
        id="p_own",
        world_id="w1",
        label="WikiPrior",
        text="own",
        score=2.0,
        meta={"prior_type": "fact", "condition": "c", "effect": "e", "domains": ["geography"]},
    )
    search = _GlobalSearch([own, other])
    explorer = CrossWorldWikiExplorer(g, search)
    out = explorer.search_related_priors("w1", query="terrain")
    assert [p.id for p in out] == ["p_other"]  # own world excluded (BR-A10)
    assert search.calls[0]["world_id"] is None  # global search
    assert "geography" in search.calls[0]["filters"]["domains"]


def test_cross_world_empty_when_no_domains() -> None:
    explorer = CrossWorldWikiExplorer(_GraphWithPriors({}), _GlobalSearch([]))
    assert explorer.search_related_priors("w1") == []


# --------------------------------------------------------------------------- #
# WikiAdmin (per-world)
# --------------------------------------------------------------------------- #
class _RecordingGraphRepo:
    def __init__(self) -> None:
        self.nodes: list = []

    def upsert_nodes(self, nodes):
        self.nodes.extend(nodes)

    def find_nodes(self, world_id, label, filters=None):
        return [n for n in self.nodes if n.label == label and n.world_id == world_id]


class _RecordingSearchRepo:
    def __init__(self) -> None:
        self.docs: list = []

    def index(self, docs):
        self.docs.extend(docs)


def test_wiki_admin_upsert_and_list_per_world() -> None:
    graph, search = _RecordingGraphRepo(), _RecordingSearchRepo()
    admin = WikiAdmin(graph, search, embedding=None)
    p = _prior(world_id="w3", condition="sea", effect="isolation")
    admin.upsert_prior(p)
    assert graph.nodes[0].label == "WikiPrior"
    assert graph.nodes[0].world_id == "w3"
    assert search.docs[0].id == p.id
    assert len(admin.list_priors("w3")) == 1
    assert len(admin.list_priors("other")) == 0
