# U4 Ontology — Business Logic Model

## OntologyBuilder.build(ingestion, topology, world_id, wiki) -> KnowledgeGraph

### 1. 그래프화 (US-3.1)
- entities/relations = ingestion에서 그대로(이미 U2 병합). 엔티티 이름→id 인덱스 구성.
- ABOUT(US-3.2 보조, Q2=A): 각 Knowledge.about_names(=ExtractedKnowledge) → 엔티티 id 해소 → `Knowledge.about_entity_ids`. 미해소 무시.

### 2. 지역 스코핑 (US-3.2, FD4-Q1/CL1=A)
- 각 입력 Knowledge에 대해:
  - `is_global=True` → 글로벌(SCOPED_TO 없음). 쿼리 시 모든 지역에 포함.
  - region_name 해소 → `ScopeLink(scope_type=direct, confidence=knowledge.confidence)`.
  - 미해소 & 비글로벌 → 미귀속 + low_confidence(보강 대상).
- inherited는 저장 안 함(쿼리 시 계산).

### 3. 고증 생성 (US-3.3, Q3=B LLM, SC-4)
- 각 지역(또는 지형 attributes 있는 지역)에 대해:
  - context = region.name/level/attributes(+ `wiki.lookup_similar(region terrain/desc)` prior 텍스트 그라운딩).
  - `llm.structured(prompt(context), CorroborationBatch)` → 최대 N(기본 2) suggestion.
  - 각 suggestion → `Knowledge(source=inferred-wiki, confidence=suggestion.confidence×0.8, derived_from_prior_ids=matched)` + 해당 지역 direct SCOPED_TO.
  - 실패/빈 결과 → graceful skip(경고). (SC-4: 최소 1건 목표.)

### 4. 의미 dedup (CL2=C: 벡터 + LLM 리랭킹)
- 대상: 입력 Knowledge + 고증 Knowledge 합집합.
- `Deduplicator.dedupe(knowledge_list)`:
  1. statements 임베딩(EmbeddingProvider.embed). (실패 시 exact 병합으로 폴백 — graceful.)
  2. 배치 내 코사인 유사도 계산, ≥ SIM_THRESHOLD 쌍을 후보로.
  3. 각 후보 쌍 `llm.structured(pair, DuplicateVerdict)` 판정.
  4. is_duplicate=True → 병합(confidence=max, refs·about·derived 합집합, canonical 유지), SCOPED_TO 재지정.
- 순수부(코사인·임계·병합)와 I/O부(embed·llm) 분리.

### 5. 출력
- KnowledgeGraph(entities, relations, knowledge=deduped, rumors=[], scopes). 저장은 U9.

## 순수 함수 (테스트)
- `cosine(a,b)`, `candidate_pairs(vectors, threshold)`, `merge_duplicates(knowledge, verdicts)`, `resolve_about(knowledge, name_to_id)`, `scope_knowledge(knowledge, region_index)`.
- LLM/Embedding/Wiki는 mock.

## Provider/Wiki 사용
- LLMProvider(고증·dedup 판정), EmbeddingProvider(dedup 유사도), CommonsenseWiki(고증 그라운딩) — 모두 생성자 주입. 실패는 graceful degrade.
