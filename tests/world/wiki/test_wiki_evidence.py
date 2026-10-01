"""U3 wiki evidence (Q4=A, BR-U3-29·31, EX-10, NFR-5·9).

The build stores the priors its wiki made by LLM fallback, so the references to them
survive; the wiki tab reads each prior with what cites it and lists the cited ids the
world does not hold.
"""

from __future__ import annotations

import pytest

from locus.shared.models import (
    ConnectionEdge,
    ConnectionKind,
    IngestionResult,
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    SourceKind,
)
from locus.world.build import BuildProviders, WorldBuilder
from locus.world.ontology.builder import OntologyBuild
from locus.world.topology.builder import TopologyBuild
from locus.world.wiki import CommonsenseWiki, WikiAdmin
from locus.world.wiki.base import WIKI_FALLBACK_MAX
from tests.shared.snapshots import snapshot_of
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _PriorLLM:
    """Answers the wiki's fallback prompt; counts the calls."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def structured(self, prompt, schema, **_kw):
        self.calls.append(prompt)
        return schema(condition=f"c{len(self.calls)}", effect=f"e{len(self.calls)}")


def _wiki(llm=None, search=None) -> CommonsenseWiki:
    return CommonsenseWiki(search or InMemorySearchRepository(), llm, world_id="w")


# --------------------------------------------------------------------------- #
# CommonsenseWiki fallback: dedupe, cap, search-only (BR-U3-29, NFR R-03)
# --------------------------------------------------------------------------- #
def test_same_normalized_query_calls_the_llm_once() -> None:
    llm = _PriorLLM()
    wiki = _wiki(llm)
    first = wiki.lookup_terrain_rule("mountain pass")
    again = wiki.lookup_terrain_rule("Mountain   PASS")
    assert len(llm.calls) == 1
    assert first[0].id == again[0].id
    assert [p.id for p in wiki.created_priors] == [first[0].id]


def test_fallback_stops_at_the_cap_and_says_so() -> None:
    llm = _PriorLLM()
    wiki = _wiki(llm)
    for i in range(WIKI_FALLBACK_MAX):
        assert wiki.lookup_similar(f"q{i}")
    assert wiki.lookup_similar("one more") == []
    assert len(llm.calls) == WIKI_FALLBACK_MAX
    assert wiki.fallback_capped


def test_search_only_lookups_never_call_the_llm() -> None:
    llm = _PriorLLM()
    assert _wiki(llm).lookup_similar("anything", fallback=False) == []
    assert _wiki(None).lookup_similar("anything") == []  # a wiki without an LLM
    assert llm.calls == []


# --------------------------------------------------------------------------- #
# Build stores fallback priors and keeps the references (EX-10, NFR-9)
# --------------------------------------------------------------------------- #
class _Ingest:
    def ingest_all(self, world_id, inputs):
        return IngestionResult(
            world_id=world_id,
            knowledge=[Knowledge(world_id=world_id, statement="k", title="k", provenance=_prov())],
        )


class _Topo:
    """Two connections ask the wiki the same terrain question."""

    def __init__(self, wiki) -> None:
        self._wiki = wiki

    def build(self, ingestion, *, world_id):
        a, b, c = (
            Region(world_id=world_id, name=n, level=RegionLevel.TOWN, provenance=_prov())
            for n in "ABC"
        )
        conns = []
        for x, y in ((a, b), (b, c)):
            prior = self._wiki.lookup_terrain_rule("mountain")[0]
            for s, t in ((x, y), (y, x)):
                conns.append(
                    ConnectionEdge(
                        world_id=world_id,
                        source_region_id=s.id,
                        target_region_id=t.id,
                        kind=ConnectionKind.ROUTE,
                        weight=0.4,
                        rationale=prior.effect,
                        wiki_prior_ref=prior.id,
                        provenance=_prov(),
                    )
                )
        return TopologyBuild(
            RegionTopology(world_id=world_id, regions=[a, b, c], connections=conns)
        )


class _Onto:
    """Corroborates one fact from a prior it finds (or makes) in the wiki."""

    def __init__(self, wiki, graph: InMemoryGraphRepository, seen: list) -> None:
        self._wiki, self._graph, self._seen = wiki, graph, seen

    def build(self, ingestion, topology, *, world_id):
        # the topology step's prior is already stored when the ontology step runs
        self._seen.extend(n.id for n in self._graph.find_nodes(world_id, "WikiPrior"))
        prior = self._wiki.lookup_similar("basin climate")[0]
        fact = Knowledge(
            world_id=world_id,
            statement="summers are hot",
            title="hot",
            derived_from_prior_ids=[prior.id],
            provenance=Provenance(source=SourceKind.INFERRED),
        )
        return OntologyBuild(
            KnowledgeGraph(world_id=world_id, knowledge=ingestion.knowledge + [fact])
        )


class _Cache:
    def get(self, world_id):  # pragma: no cover - the builder never reads
        raise AssertionError

    def invalidate(self, world_id) -> None: ...


def _build():
    graph, search, llm, seen = (
        InMemoryGraphRepository(),
        InMemorySearchRepository(),
        _PriorLLM(),
        [],
    )
    holder: dict = {}

    def wiki_factory(world_id, _llm, _emb):
        holder["wiki"] = CommonsenseWiki(search, llm, world_id=world_id)
        return holder["wiki"]

    builder = WorldBuilder(
        graph,
        search,
        _Cache(),
        providers=BuildProviders(),
        ingestion_factory=lambda llm_, vlm: _Ingest(),
        topology_factory=lambda wiki: _Topo(wiki),
        ontology_factory=lambda llm_, emb, wiki: _Onto(wiki, graph, seen),
        wiki_factory=wiki_factory,
    )
    report = builder.build("w", inputs=None)
    return report, graph, search, llm, seen


def test_ex10_fallback_priors_are_stored_and_referenced() -> None:
    """EX-10: a terrain with no search hit makes one LLM prior; it is stored and the
    connection keeps its reference. The ontology's prior is stored too."""
    report, graph, search, llm, seen = _build()
    assert report.ok, report.warnings
    assert len(llm.calls) == 2  # one terrain question (asked twice) + one corroboration
    stored = {n.id for n in graph.find_nodes("w", "WikiPrior")}
    assert report.priors_created == 2 == len(stored)
    refs = {e.properties.get("wiki_prior_ref") for e in graph.get_edges("w", ["CONNECTED_TO"])}
    assert refs and refs <= stored  # no connection ref is broken (NFR-9)
    assert len(seen) == 1 and set(seen) <= stored  # topology prior stored before ontology
    for e in graph.get_edges("w", ["DERIVED_FROM"]):  # every endpoint exists (NFR-9)
        assert graph.get_node("w", e.target_id) is not None
    assert {d.label for d in search.docs.values()} >= {"WikiPrior"}


# --------------------------------------------------------------------------- #
# WikiAdmin reads and delete (BR-U3-31, BLM §5.2)
# --------------------------------------------------------------------------- #
class _SnapshotCache:
    def __init__(self, graph: InMemoryGraphRepository) -> None:
        self._graph = graph
        self.invalidated: list[str] = []

    def get(self, world_id):
        from locus.knowledge.loader import WorldLoader

        return WorldLoader(self._graph).load(world_id)

    def invalidate(self, world_id) -> None:
        self.invalidated.append(world_id)


def test_wiki_tab_reads_usages_and_broken_refs_after_a_delete() -> None:
    report, graph, search, _llm, _seen = _build()
    admin = WikiAdmin(graph, search, cache=_SnapshotCache(graph))
    usages = admin.prior_refs("w")
    assert len(usages) == 2
    terrain = next(u for u in usages if u.connections)
    assert len(terrain.connections) == 2  # A–B and B–C, one key per pair
    corroborated = next(u for u in usages if u.knowledge)
    assert [k.name for k in corroborated.knowledge] == ["hot"]
    assert admin.broken_refs("w") == []

    admin.delete_prior("w", terrain.prior.id)
    assert ("w", terrain.prior.id) not in search.docs
    broken = admin.broken_refs("w")
    assert [b.ref_id for b in broken] == [terrain.prior.id]
    assert len(broken[0].connections) == 2


def test_delete_missing_prior_still_clears_its_search_doc() -> None:
    """NFR R-01: a retry after a cut between graph and search cleans the document."""
    report, graph, search, _llm, _seen = _build()
    admin = WikiAdmin(graph, search, cache=_SnapshotCache(graph))
    pid = admin.list_priors("w")[0].id
    graph.delete_node("w", pid)  # the graph delete happened, the search delete did not
    with pytest.raises(LookupError):
        admin.delete_prior("w", pid)
    assert ("w", pid) not in search.docs


def test_list_priors_returns_models() -> None:
    _report, graph, search, _llm, _seen = _build()
    priors = WikiAdmin(graph, search).list_priors("w")
    assert all(p.world_id == "w" and p.effect for p in priors)


def test_citation_maps_on_a_plain_snapshot() -> None:
    from locus.shared.models import PriorType, WikiPrior
    from locus.world.wiki.admin import broken, prior_ref_view, usages

    prior = WikiPrior(
        world_id="w", prior_type=PriorType.FACT, condition="c", effect="e", provenance=_prov()
    )
    k = Knowledge(
        world_id="w",
        statement="s",
        title="t",
        derived_from_prior_ids=[prior.id, "gone"],
        provenance=_prov(),
    )
    snap = snapshot_of(
        KnowledgeGraph(world_id="w", knowledge=[k]), RegionTopology(world_id="w", regions=[])
    )
    assert usages(snap, [prior])[0].knowledge[0].id == k.id
    assert [b.ref_id for b in broken(snap, [prior])] == ["gone"]
    assert prior_ref_view("gone", {}).broken
    assert prior_ref_view(prior.id, {prior.id: prior}).effect == "e"


def test_c9_refs_reads_one_snapshot_and_no_prior_nodes() -> None:
    """U3 review C9: the wiki tab's two lists come from one snapshot read; the
    snapshot's priors are the stored ones (no extra ``find_nodes`` on WikiPrior)."""
    report, graph, search, _llm, _seen = _build()
    cache = _SnapshotCache(graph)
    admin = WikiAdmin(graph, search, cache=cache)
    loads: list[str] = []
    warm = cache.get("w")  # a warm cache, as in the app: the load is not what this counts
    cache.get = lambda wid: (loads.append(wid), warm)[1]  # type: ignore[method-assign]
    prior_reads: list[str] = []
    real_find = graph.find_nodes

    def find(world_id, label, filters=None):
        if label == "WikiPrior":
            prior_reads.append(world_id)
        return real_find(world_id, label, filters)

    usages, broken = admin.refs("w")
    graph.find_nodes = find  # type: ignore[method-assign]
    usages, broken = admin.refs("w")
    assert len(loads) == 2 and prior_reads == []  # one snapshot per call, no prior scan
    assert [u.prior.id for u in usages] == [u.prior.id for u in admin.prior_refs("w")]
    assert broken == admin.broken_refs("w")
