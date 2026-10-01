"""U4 Ontology tests — similarity, dedup, corroboration, scoping, builder (mocked)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.shared.models import (
    IngestionResult,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeType,
    SourceKind,
)
from locus.world.ontology import (
    Deduplicator,
    OntologyBuilder,
    candidate_pairs,
    cosine,
    merge_duplicates,
    scope_knowledge,
)
from locus.world.ontology.schemas import (
    CorroborationBatch,
    CorroborationSuggestion,
    DuplicateVerdict,
)


def _prov(src: SourceKind = SourceKind.INPUT) -> Provenance:
    return Provenance(source=src)


def _k(
    statement: str, *, conf: float = 0.8, region: str | None = None, glob: bool = False
) -> Knowledge:
    return Knowledge(
        world_id="w",
        statement=statement,
        title=statement,
        confidence=conf,
        region_hint=region,
        is_global=glob,
        provenance=_prov(),
    )


def _region(name: str) -> Region:
    return Region(world_id="w", name=name, level=RegionLevel.TOWN, provenance=_prov())


# --------------------------------------------------------------------------- #
# similarity
# --------------------------------------------------------------------------- #
def test_cosine_identical_and_orthogonal() -> None:
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_cosine_degenerate() -> None:
    assert cosine([], [1.0]) == 0.0
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


@given(
    st.lists(st.floats(min_value=-5, max_value=5), min_size=3, max_size=3),
    st.lists(st.floats(min_value=-5, max_value=5), min_size=3, max_size=3),
)
def test_cosine_bounded(a: list[float], b: list[float]) -> None:
    assert -1.0001 <= cosine(a, b) <= 1.0001


def test_candidate_pairs_threshold() -> None:
    vecs = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
    assert candidate_pairs(vecs, 0.86) == [(0, 1)]


# --------------------------------------------------------------------------- #
# merge_duplicates (pure)
# --------------------------------------------------------------------------- #
def test_merge_duplicates_keeps_max_confidence() -> None:
    a, b, c = _k("x", conf=0.4), _k("x2", conf=0.9), _k("y", conf=0.5)
    merged, remap = merge_duplicates([a, b, c], [[0, 1], [2]])
    assert len(merged) == 2
    canonical = next(m for m in merged if m.id == b.id)
    assert canonical.confidence == 0.9
    assert remap[a.id] == b.id


# --------------------------------------------------------------------------- #
# Deduplicator
# --------------------------------------------------------------------------- #
class _FakeEmbedding:
    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors

    @property
    def dimension(self) -> int:
        return len(self._vectors[0]) if self._vectors else 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._vectors


class _DupLLM:
    def structured(self, prompt, schema, *, system=None):
        return DuplicateVerdict(is_duplicate=True, reason="same")


def test_deduplicator_merges_confirmed_pair() -> None:
    k0, k1, k2 = (
        _k("The river floods", conf=0.5),
        _k("River floods yearly", conf=0.7),
        _k("Cold north"),
    )
    embedding = _FakeEmbedding([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
    deduped, remap = Deduplicator(embedding, _DupLLM()).dedupe([k0, k1, k2])
    assert len(deduped) == 2
    assert remap[k0.id] == remap[k1.id]


def test_deduplicator_exact_fallback_without_providers() -> None:
    k0, k1 = _k("Same fact"), _k("same  FACT")  # normalized equal
    deduped, _ = Deduplicator(None, None).dedupe([k0, k1])
    assert len(deduped) == 1


# --------------------------------------------------------------------------- #
# scope_knowledge
# --------------------------------------------------------------------------- #
def test_scope_knowledge_direct_global_unscoped() -> None:
    town = _region("Rivertown")
    k_direct = _k("market on sundays", region="Rivertown")
    k_global = _k("sun rises in the east", glob=True)
    k_unscoped = _k("rumor", region="Nowhere")
    scopes, unscoped, _warnings = scope_knowledge([k_direct, k_global, k_unscoped], [town])
    assert len(scopes) == 1
    assert scopes[0].knowledge_id == k_direct.id
    assert scopes[0].scope_type == ScopeType.DIRECT
    assert unscoped == [k_unscoped.id]


# --------------------------------------------------------------------------- #
# Corroboration + Builder (mocked LLM)
# --------------------------------------------------------------------------- #
class _SmartLLM:
    """Returns CorroborationBatch or DuplicateVerdict depending on requested schema."""

    def __init__(self, corr_items: list[CorroborationSuggestion] | None = None) -> None:
        self._corr = corr_items or []

    def structured(self, prompt, schema, *, system=None):
        if schema is CorroborationBatch:
            return CorroborationBatch(items=self._corr)
        if schema is DuplicateVerdict:
            return DuplicateVerdict(is_duplicate=False)
        return schema()


def test_corroboration_confidence_discounted_and_scoped() -> None:
    from locus.world.ontology import CorroborationGenerator

    town = _region("Basinville")
    llm = _SmartLLM([CorroborationSuggestion(statement="hot and dry", confidence=1.0)])
    gen = CorroborationGenerator(llm, wiki=None, max_per_region=2)
    knowledge, scopes = gen.generate([town], world_id="w")
    assert len(knowledge) == 1
    assert abs(knowledge[0].confidence - 0.8) < 1e-9  # 1.0 * 0.8 discount
    assert knowledge[0].provenance.source == SourceKind.INFERRED
    assert scopes[0].region_id == town.id


def test_ontology_builder_end_to_end() -> None:
    town = _region("Rivertown")
    topo = RegionTopology(world_id="w", regions=[town])
    ingestion = IngestionResult(
        world_id="w",
        knowledge=[
            _k("market on sundays", region="Rivertown"),
            _k("sun rises in the east", glob=True),
        ],
    )
    llm = _SmartLLM([CorroborationSuggestion(statement="fed by a river", confidence=0.9)])
    embedding = _FakeEmbedding([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])  # all distinct -> no merge

    kg = (
        OntologyBuilder(llm=llm, embedding=embedding, wiki=None)
        .build(ingestion, topo, world_id="w")
        .kg
    )
    # 2 input + 1 corroboration = 3 knowledge
    assert len(kg.knowledge) == 3
    # direct scope for the region-hinted input + the corroboration; global has none
    assert len(kg.scopes) == 2
    assert all(s.scope_type == ScopeType.DIRECT for s in kg.scopes)


# --------------------------------------------------------------------------- #
# U2 Step 7 — unscoped ids survive dedup on canonical ids (RE A4 / BR-U2-14)
# --------------------------------------------------------------------------- #
def test_unscoped_ids_are_canonical_after_dedup() -> None:
    from locus.shared.models import IngestionResult, RegionTopology

    town = _region("Rivertown")
    k1 = _k("nobody knows where", region="Nowhere")
    k2 = _k("nobody knows where", region="Nowhere")  # exact duplicate -> merged into k1
    ingestion = IngestionResult(world_id="w", knowledge=[k1, k2])
    topo = RegionTopology(world_id="w", regions=[town])
    result = OntologyBuilder(llm=None, embedding=None, wiki=None).build(
        ingestion, topo, world_id="w"
    )
    kept = {k.id for k in result.kg.knowledge}
    assert set(result.kg.unscoped_knowledge_ids) <= kept
    assert len(result.kg.unscoped_knowledge_ids) == len(kept)  # every kept item is unscoped
    assert any("Nowhere" in w.message for w in result.warnings)


def test_u7_the_ontology_builder_hands_its_dedup_bar_to_the_deduplicator(monkeypatch) -> None:
    """FR-A7: ONTOLOGY_DEDUP_THRESHOLD reaches the dedup step (world_tuning -> builder)."""
    from locus.world.ontology import builder as ob

    seen = {}

    class Spy:
        def __init__(self, embedding, llm, *, threshold):
            seen["threshold"] = threshold

        def dedupe(self, knowledge):
            return knowledge, {}

    monkeypatch.setattr(ob, "Deduplicator", Spy)
    from locus.shared.models import IngestionResult, RegionTopology

    ob.OntologyBuilder(dedup_threshold=0.91).build(
        IngestionResult(world_id="w"), RegionTopology(world_id="w"), world_id="w"
    )
    assert seen["threshold"] == 0.91
