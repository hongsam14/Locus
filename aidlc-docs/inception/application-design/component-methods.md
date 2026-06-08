# Component Methods — Locus

메서드 시그니처(고수준)와 입출력. **상세 비즈니스 규칙·알고리즘은 Functional Design(per-unit)에서 정의.** 타입은 `locus/models`의 Pydantic 모델 기준(파이썬 의사 시그니처).

---

## C1. Ingestion — `Ingestor` 계열
```python
class TextIngestor:
    def extract(self, memo: str, *, world_id: str) -> IngestionResult: ...
        # 메모 → 엔티티/관계 후보(+confidence). LLM 사용.

class MapImageIngestor:
    def extract(self, image: bytes, *, world_id: str) -> IngestionResult: ...
        # 지도 이미지 → 지역/지형 피처(+위치 단서, confidence). VLM 사용.

class StructuredMapIngestor:
    def parse(self, doc: dict, *, world_id: str) -> IngestionResult: ...
        # GeoJSON/노드-엣지 → 지역·연결. 스키마 검증; 위반 시 IngestionResult.errors.

class ConceptArtIngestor:
    def extract(self, image: bytes, *, world_id: str) -> IngestionResult: ...
        # 컨셉아트 → 보조 단서(낮은 weight).
```
`IngestionResult`: `entities`, `relations`, `region_hints`, `terrain_features`, `low_confidence_items`, `errors`.

## C2. Topology — `TopologyBuilder`
```python
class TopologyBuilder:
    def build(self, ingestion: IngestionResult, *, world_id: str,
              wiki: CommonsenseWiki) -> RegionTopology: ...
    def assign_hierarchy(self, regions: list[Region]) -> list[Region]: ...   # 대륙>지방>마을>구역
    def compute_edge_weights(self, topo: RegionTopology,
                             wiki: CommonsenseWiki) -> RegionTopology: ...    # 지형 prior 반영 weight + 근거
```

## C3. Ontology — `OntologyBuilder`
```python
class OntologyBuilder:
    def build(self, ingestion: IngestionResult, topo: RegionTopology, *,
              world_id: str, wiki: CommonsenseWiki) -> KnowledgeGraph: ...
    def scope_to_regions(self, kg: KnowledgeGraph, topo: RegionTopology) -> KnowledgeGraph: ...  # 귀속+상속
    def generate_corroborations(self, kg: KnowledgeGraph, topo: RegionTopology,
                                wiki: CommonsenseWiki) -> list[KnowledgeItem]: ...  # 고증(출처=wiki)
    def merge_duplicates(self, kg: KnowledgeGraph) -> KnowledgeGraph: ...
```

## C4. Consensus — `ConsensusEngine` / `PropagationResolver`
```python
class ConsensusEngine:                         # 정적 전처리
    def precompute_direct_scopes(self, world_id: str) -> None: ...   # 지역별 직접 보유 지식 저장

class PropagationResolver:                      # 쿼리 시점
    def resolve(self, region_id: str) -> ConsensusView: ...
        # 토폴로지 순회로 전파/소문 범위 계산
    def apply_distortion(self, item: KnowledgeItem, path_weight: float
                         ) -> KnowledgeItem | KnowledgeVariant: ...
        # 경미→confidence 감쇠 / 변형→variant(distorted_from)
```
`ConsensusView`: `direct[]`, `shared[]`, `propagated[]`, `rumors[]`(variant), `unknown_count`.

## C5. Commonsense Wiki — `CommonsenseWiki`
```python
class CommonsenseWiki:
    def lookup_terrain_rule(self, feature: TerrainFeature) -> list[WikiPrior]: ...   # 산맥→교류 지연 등
    def lookup_similar(self, query: str, k: int = 5) -> list[WikiPrior]: ...          # 의미 검색(분지→데스밸리)
    def build_from_real_world(self, sources: IngestionResult) -> None: ...            # 동일 파이프라인 wiki 모드
    def upsert_prior(self, prior: WikiPrior) -> WikiPrior: ...                        # 편집
```

## C6. Augmentation — `AugmentationEngine` / `AugmentationGraph`
```python
class AugmentationEngine:
    def detect_issues(self, world_id: str
                      ) -> list[Issue]: ...   # 빈틈/모순(A) + Wiki 충돌(B) + 저신뢰(C)
    def generate_questions(self, issues: list[Issue]) -> list[AugmentationQuestion]: ...
    def apply_answer(self, answer: AugmentationAnswer) -> ChangeSet: ...   # 그래프 갱신
    def revert(self, change_id: str) -> None: ...                          # 되돌리기

class AugmentationGraph:                       # LangGraph 루프(국소)
    def run_session(self, world_id: str) -> AugmentationSession: ...       # detect→ask→apply→재detect 수렴
```

## C7. Query — `QueryEngine`
```python
class QueryEngine:
    def knowledge_for_region(self, region_id: str, *,
                             include_rumors: bool = True) -> QueryResult: ...
    def diff_regions(self, region_a: str, region_b: str) -> RegionDiff: ...   # 공유 vs 고유
```
`QueryResult`: `region_id`, `items[]`(각 항목: scope, confidence, is_variant, source), `shared_ids[]`, `unique_ids[]`.

## C8. LLM Provider — `LLMProvider` / `VLMProvider`
```python
class LLMProvider(Protocol):
    def complete(self, prompt: str, **opts) -> str: ...
    def structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel: ...

class VLMProvider(Protocol):
    def analyze_image(self, image: bytes, prompt: str, **opts) -> str: ...

class ProviderFactory:
    def llm(self) -> LLMProvider: ...     # 기본 OpenAI (LangChain)
    def vlm(self) -> VLMProvider: ...
```

## C9. Storage — `GraphRepository` / `SearchRepository`
```python
class GraphRepository(Protocol):
    def upsert_nodes(self, nodes: list[Node]) -> None: ...
    def upsert_edges(self, edges: list[Edge]) -> None: ...
    def traverse(self, start: str, spec: TraversalSpec) -> list[Path]: ...
    def get_region_subtree(self, region_id: str) -> list[Region]: ...

class SearchRepository(Protocol):
    def index(self, docs: list[SearchDoc]) -> None: ...
    def hybrid_search(self, query: str, k: int, filters: dict | None = None
                      ) -> list[SearchHit]: ...   # 벡터 + BM25
```

## Services (요약 — 상세는 services.md)
```python
class PipelineOrchestrator:
    def build_world(self, world_id: str, inputs: WorldInputs) -> BuildReport: ...
        # ingestion → topology → ontology → consensus.precompute (동기 순차)
```
