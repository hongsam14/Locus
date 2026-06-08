# U4 Ontology — Domain Entities & Schemas

결정: FD4-Q2=A, Q3=B(LLM 고증), Q5=A(prior×0.8), **CL1=A(글로벌 지식)**, **CL2=C(벡터+LLM 리랭킹 dedup)**.

## Model additions (U1/U2 확장 — additive)
- `locus/models`:
  - `ScopeType.GLOBAL` 추가.
  - `Knowledge.is_global: bool = False` 추가. (글로벌 지식은 SCOPED_TO 없이 모든 지역 쿼리에 포함.)
- `locus/ingestion/schemas.py`:
  - `ExtractedKnowledge.is_global: bool = False` (LLM이 world 전역 사실로 판단 시 True).
- `locus/ingestion/mapping.to_knowledge` — is_global 전달.

## Input → Output
- Input: `IngestionResult`(entities/relations/knowledge), `RegionTopology`(regions), `CommonsenseWiki`, providers(LLM/Embedding).
- Output: `KnowledgeGraph { world_id, entities, relations, knowledge, rumors(=[]), scopes }`.
  - rumors는 U4에서 생성 안 함(왜곡은 U5 Consensus). scopes = SCOPED_TO(ScopeLink, scope_type=direct).

## 고증 생성 스키마 (Q3=B, LLM)
```text
CorroborationSuggestion { statement, topic?, rationale, confidence(0~1) }
CorroborationBatch { items: [CorroborationSuggestion] }   # 지역당 최대 N(기본 2)
```
- 입력 컨텍스트: 지역 name/level/attributes(지형) + (가용 시) `wiki.lookup_similar` prior 텍스트(그라운딩).
- 출력 → `Knowledge(source=inferred-wiki, generated_by="llm", derived_from_prior_ids=[matched wiki prior ids], confidence = prior_conf×0.8 또는 suggestion.confidence×0.8)`, 해당 지역에 direct SCOPED_TO.

## 의미 dedup 스키마 (CL2=C)
```text
DuplicateVerdict { is_duplicate: bool, canonical_index: int, reason }
```
- 흐름: 후보 지식 statement 임베딩(EmbeddingProvider) → 배치 내 코사인 유사도 ≥ SIM_THRESHOLD(기본 0.86) 쌍 후보 → 각 후보 쌍을 LLM이 판정(DuplicateVerdict) → 중복 확정 시 병합(confidence=max, refs 합집합, canonical 유지).
- 결정성 한계: LLM 판정은 비결정적 → 테스트는 mock. 코사인/임계·병합 로직은 순수(테스트).

## 비고
- 상속(inherited) 스코프는 저장 안 함 — 쿼리 시 CONTAINS 순회로 계산(U5/U8, FD1-Q3=A).
- 미해소·비글로벌 지식 → 미귀속 + low_confidence(보강 대상, U7).
