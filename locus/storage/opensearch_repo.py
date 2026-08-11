"""OpenSearch implementation of SearchRepository (US-9.2).

Single index ``locus_search`` with a kNN vector field + BM25 text field; every
query is filtered by ``world_id`` (BR-19, ND1-Q2=A). The ``opensearchpy``
package is imported lazily so the module is importable/testable without it.
"""

from __future__ import annotations

from ..models import SearchDoc
from .base import SearchHit, SearchRepository


def index_mapping(vector_dimension: int) -> dict:
    """OpenSearch index body: kNN settings + field mappings."""
    return {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100,
                "number_of_shards": 1,
                "number_of_replicas": 0,
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "world_id": {"type": "keyword"},
                "label": {"type": "keyword"},
                "text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": vector_dimension,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib",
                        "parameters": {"ef_construction": 128, "m": 16},
                    },
                },
                "meta": {"type": "object", "enabled": True},
            }
        },
    }


def build_search_body(
    world_id: str | None,
    query_text: str,
    query_embedding: list[float] | None,
    k: int,
    filters: dict | None,
) -> dict:
    """Construct the hybrid (BM25 + kNN) search body.

    ``world_id=None`` omits the partition filter for the designer's cross-world
    prior search (FR-IM1.4). List-valued filters use ``terms`` (match-any), so a
    ``domains`` overlap filter works.
    """
    filter_clauses: list[dict] = []
    if world_id is not None:
        filter_clauses.append({"term": {"world_id": world_id}})
    for key, val in (filters or {}).items():
        if isinstance(val, (list, tuple, set)):
            filter_clauses.append({"terms": {key: list(val)}})
        else:
            filter_clauses.append({"term": {key: val}})

    should: list[dict] = []
    if query_text:
        should.append({"match": {"text": {"query": query_text}}})
    if query_embedding:
        should.append({"knn": {"embedding": {"vector": query_embedding, "k": k}}})

    return {
        "size": k,
        "query": {
            "bool": {
                "filter": filter_clauses,
                "should": should,
                "minimum_should_match": 1 if should else 0,
            }
        },
    }


class OpenSearchRepository(SearchRepository):
    def __init__(self, *, url: str, index: str, vector_dimension: int) -> None:
        self._url = url
        self._index = index
        self._dim = vector_dimension
        self._client = None

    # -- lifecycle -------------------------------------------------------- #
    def connect(self) -> None:
        from opensearchpy import OpenSearch

        self._client = OpenSearch(hosts=[self._url])
        self._client.info()

    def disconnect(self) -> None:
        self._client = None

    def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.cluster.health()
            return True
        except Exception:
            return False

    def _require_client(self):
        if self._client is None:
            raise RuntimeError("OpenSearchRepository not connected; call connect() first.")
        return self._client

    # -- schema ----------------------------------------------------------- #
    def ensure_index(self) -> None:
        client = self._require_client()
        if not client.indices.exists(index=self._index):
            client.indices.create(index=self._index, body=index_mapping(self._dim))

    # -- writes / reads --------------------------------------------------- #
    def index(self, docs: list[SearchDoc]) -> None:
        if not docs:
            return
        client = self._require_client()
        bulk: list[dict] = []
        for doc in docs:
            bulk.append({"index": {"_index": self._index, "_id": doc.id}})
            bulk.append(doc.model_dump())
        client.bulk(body=bulk, refresh=True)

    def hybrid_search(
        self,
        world_id: str | None,
        query_text: str,
        query_embedding: list[float] | None = None,
        k: int = 5,
        filters: dict | None = None,
    ) -> list[SearchHit]:
        client = self._require_client()
        body = build_search_body(world_id, query_text, query_embedding, k, filters)
        response = client.search(index=self._index, body=body)
        hits: list[SearchHit] = []
        for hit in response.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            hits.append(
                SearchHit(
                    id=src.get("id", hit.get("_id", "")),
                    world_id=src.get("world_id", world_id or ""),
                    label=src.get("label", ""),
                    text=src.get("text", ""),
                    score=float(hit.get("_score") or 0.0),
                    meta=src.get("meta", {}),
                )
            )
        return hits

    def delete_world(self, world_id: str) -> None:
        client = self._require_client()
        client.delete_by_query(
            index=self._index,
            body={"query": {"term": {"world_id": world_id}}},
            refresh=True,
        )
