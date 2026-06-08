# U1 Foundation — Logical Components

| 논리 컴포넌트 | 책임 | 위치(예정) | 패턴 |
|---|---|---|---|
| **Settings** | `.env`/환경변수 로드(키·접속·모델명) | `locus/config/settings.py` | 12-factor |
| **ProviderFactory** | 설정 기반 LLM/VLM/Embedding 구현 선택 | `locus/llm/factory.py` | Factory |
| **LLMProvider / VLMProvider / EmbeddingProvider** | 외부 모델 호출 포트 + OpenAI(LangChain) 어댑터 | `locus/llm/` | Ports&Adapters |
| **RetryPolicy** | 재시도(3회·지수백오프)+타임아웃(30s) 데코레이터/래퍼 | `locus/llm/retry.py` (tenacity) | Retry/Timeout |
| **GraphRepository (port)** | 노드/엣지 upsert·조회·순회 포트 | `locus/storage/base.py` | Repository |
| **Neo4jGraphRepository** | Neo4j 어댑터(드라이버, Cypher, 제약 관리) | `locus/storage/neo4j_repo.py` | Adapter |
| **SearchRepository (port)** | 색인·하이브리드 검색 포트 | `locus/storage/base.py` | Repository |
| **OpenSearchRepository** | OpenSearch 어댑터(단일 인덱스, kNN+BM25, world_id 필터) | `locus/storage/opensearch_repo.py` | Adapter |
| **CommonsenseWiki (interface)** | lookup_terrain_rule / lookup_similar + LLM 폴백 | `locus/commonsense_wiki/base.py` | Strategy/Fallback |
| **Domain Models** | Pydantic 노드/관계/IO 모델 + Enum | `locus/models/` | Value/DTO |
| **Schema Initializer** | Neo4j 제약/인덱스 + OpenSearch 인덱스 매핑 부트스트랩 | `locus/storage/schema.py` | Migration(경량) |
| **BuildReport / warnings** | 빌드 결과·경고(graceful degrade) 집계 | `locus/models/reports.py` | — |

## 컴포넌트 상호작용 (요지)
```
Settings → ProviderFactory → {LLM,VLM,Embedding}Provider (RetryPolicy로 래핑)
코어 모듈 → GraphRepository(port) → Neo4jGraphRepository → Neo4j
코어 모듈 → SearchRepository(port) → OpenSearchRepository → OpenSearch
코어 모듈 → CommonsenseWiki → SearchRepository(__realworld__) → (miss) → LLMProvider 폴백
SchemaInitializer → Neo4j 제약/인덱스 + OpenSearch 매핑 생성(부트스트랩)
```

## 제외 (ND1-Q3=B)
- EmbeddingCache / lookup 캐시 컴포넌트 — 미생성(매 호출 직접 수행).

## 인덱스/제약 부트스트랩 (SchemaInitializer)
- Neo4j: 라벨별 유니크 제약(Region/Entity), `world_id` 인덱스.
- OpenSearch: `locus_search` 인덱스 — `world_id`(keyword), `label`(keyword), `text`(text/BM25), `embedding`(knn_vector, 차원=임베딩 모델 출력), `meta`(object).
