# U1 Foundation — Business Logic Model

U1 범위의 핵심 로직(기술 무관). 저장소/제공자 구현 세부는 NFR/Infra·CodeGen에서.

## 1. Repository 계약 (포트)

### GraphRepository (포트)
- `upsert_nodes(nodes)` / `upsert_edges(edges)` — world_id·유니크 제약 준수, idempotent.
- `get_node(id)` / `find_nodes(world_id, label, filters)`.
- `get_region_subtree(region_id)` — `CONTAINS` 하위 트리.
- `get_region_ancestors(region_id)` — 상속 계산용 조상 경로.
- `traverse(start_id, spec)` — `CONNECTED_TO` 가중 순회(컨센서스 전파에서 사용).
- `delete_subgraph(world_id)` — 세계 초기화.

### SearchRepository (포트)
- `index(docs: list[SearchDoc])` — 임베딩 포함 색인(upsert).
- `hybrid_search(world_id, query, k, filters)` — 벡터 + BM25 결합, `SearchHit[]`.
- `delete(world_id)`.

### 규칙
- 코어 모듈은 **포트 인터페이스에만** 의존(AD-Q5=A). Neo4j/OpenSearch 어댑터가 구현.
- 모든 쓰기는 `world_id` 스코프. 교차 세계 쓰기 금지.

## 2. 임베딩 생성 흐름
1. 색인 대상(Knowledge/Entity/WikiPrior/Rumor) 생성·수정 시 `text` 구성(name/statement + description).
2. `EmbeddingProvider.embed(text)` → vector (LLM provider 추상화 경유 또는 전용 임베딩 모델; 모델 선택은 NFR).
3. `SearchDoc` 구성 후 `SearchRepository.index`.
4. `embedding_ref`로 노드와 색인 문서 연결.

## 3. LLM/VLM Provider 추상화 (포트)
- `LLMProvider.complete(prompt)`, `.structured(prompt, schema)` ; `VLMProvider.analyze_image(img, prompt)`.
- `EmbeddingProvider.embed(text) -> vector`.
- `ProviderFactory`가 설정 기반으로 구현 선택(기본 OpenAI via LangChain). (AD-Q4=C)

## 4. CommonsenseWiki lookup + 폴백 흐름 (FD/UOW-Q5=X, CL1=A)
```
lookup_terrain_rule(feature) / lookup_similar(query, k):
  1. SearchRepository.hybrid_search(world_id="__realworld__", ...) 로 WikiPrior 검색
  2. hit 있으면 → 해당 WikiPrior 반환(+provenance: source=wiki)
  3. hit 없거나 임계 미만이면 → LLMProvider 폴백 추론
       - 가용한 wiki 컨텍스트(있다면)를 프롬프트에 포함(grounding)
       - 결과 provenance: source=inferred-wiki, generated_by=LLM
  4. (선택) 폴백 결과를 신규 WikiPrior 후보로 적재(저신뢰 표시)
```
- Wiki가 비어 있어도(초기) 안전 동작 → U3/U4가 일찍 진행 가능.
- 운영상 사용자가 실세계 자료를 ingest해 Wiki를 먼저 채우면 hit 비율↑.

## 5. Provenance 기록 (Q6=A)
- 모든 생성/추론 항목에 `Provenance{source, generated_by, refs[], note}` 필수.
- `source ∈ {input, inferred-wiki, augmentation}`; 고증·가중 항목은 `DERIVED_FROM`(WikiPrior)로 근거 연결.
