"""Common-sense Wiki lookup tests — single-world hit vs miss->LLM fallback (mocked)."""

from __future__ import annotations

from locus.commonsense_wiki.base import CommonsenseWiki, _PriorSuggestion
from locus.models import SearchHit, SourceKind


class _FakeSearch:
    def __init__(self, hits: list[SearchHit]) -> None:
        self._hits = hits
        self.calls: list[dict] = []

    def hybrid_search(self, world_id, query_text, query_embedding=None, k=5, filters=None):
        self.calls.append({"world_id": world_id, "query_text": query_text, "filters": filters})
        return self._hits


class _FakeLLM:
    def __init__(self) -> None:
        self.called = False

    def complete(self, prompt, *, system=None):  # pragma: no cover - unused
        return ""

    def structured(self, prompt, schema, *, system=None):
        self.called = True
        return _PriorSuggestion(
            condition="mountain range between regions",
            effect="connection weight reduced; slower information flow",
            description="logistics prior",
            confidence=0.7,
        )


def test_lookup_hit_returns_wiki_prior_without_llm() -> None:
    hit = SearchHit(
        id="p1",
        world_id="w1",
        label="WikiPrior",
        text="mountain blocks travel",
        score=2.5,
        meta={
            "prior_type": "terrain_rule",
            "condition": "mountain range",
            "effect": "slower exchange",
            "domains": ["geography", "logistics"],
            "confidence": 1.0,
        },
    )
    search = _FakeSearch([hit])
    llm = _FakeLLM()
    wiki = CommonsenseWiki(search, llm, embedding=None, world_id="w1")

    priors = wiki.lookup_terrain_rule("mountain range between A and B")

    assert len(priors) == 1
    assert priors[0].id == "p1"
    assert priors[0].world_id == "w1"
    assert "geography" in [str(d) for d in priors[0].domains]
    assert priors[0].provenance.source == SourceKind.INPUT
    assert llm.called is False
    # scoped to THIS world's partition + filtered to WikiPrior label (BR-A9)
    assert search.calls[0]["world_id"] == "w1"
    assert search.calls[0]["filters"] == {"label": "WikiPrior"}


def test_lookup_miss_triggers_llm_fallback() -> None:
    search = _FakeSearch([])  # no hits
    llm = _FakeLLM()
    wiki = CommonsenseWiki(search, llm, embedding=None, world_id="w1")

    priors = wiki.lookup_similar("climate of a basin region")

    assert len(priors) == 1
    assert llm.called is True
    assert priors[0].world_id == "w1"
    assert priors[0].provenance.source == SourceKind.INFERRED_WIKI
    assert priors[0].effect.startswith("connection weight")
