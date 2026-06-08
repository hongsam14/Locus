# U4 Ontology — Functional Design Plan

U4는 `IngestionResult` + `RegionTopology`(+ Wiki)로 **지식 그래프**를 만듭니다(FR-C, US-3.1~3.3): 엔티티/관계 그래프화, 지식의 **지역 스코핑**(SCOPED_TO), **고증 지식 자동 생성**, 중복 병합.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD4-Q1 — 지식의 지역 귀속(SCOPED_TO)
ExtractedKnowledge의 `region_name`으로 지역에 귀속할 때, 지역이 없으면?

A) region_name 해소되면 **direct 스코프**; 미해소/없음이면 **미귀속 + 보강 대상(low confidence)** 표시 (Recommended — 상속은 쿼리 시 계산, FD1-Q3)
B) 미해소 시 최상위 지역(또는 World)에 임시 귀속
C) 미해소 지식은 폐기
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 글로벌 지식이라는 개념이 생겨야함. (ex: [world_id]에는 해가 동쪽에서 뜬다.)

## Question FD4-Q2 — 지식↔엔티티(ABOUT) 연결
ExtractedKnowledge.about_names를 엔티티에 연결?

A) about_names를 엔티티 이름으로 해소해 ABOUT 엣지 생성(미해소는 무시) (Recommended)
B) 연결 안 함(MVP 제외)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD4-Q3 — 고증(corroboration) 생성 트리거/방식 (SC-4)
Wiki 기반 추가 지식 생성은?

A) **지역 attributes(지형/기후)** 기반 — 각 지역의 지형 단서로 `wiki.lookup_similar` → 매칭 prior를 고증 Knowledge로 변환(source=inferred-wiki, DERIVED_FROM, 지역에 direct 스코프). 지역당 최대 N(기본 2) (Recommended — 결정적·SC-4 충족)
B) LLM이 지역 맥락으로 자유 생성(structured) — 풍부하나 비결정적
C) 둘 다(Wiki 우선 + 부족분 LLM)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question FD4-Q4 — 중복 병합
지식 중복은?

A) 정규화 statement 기준 병합(confidence=max), 엔티티는 U2에서 병합됨(추가 cross-check만) (Recommended)
B) 병합 안 함
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 벡터 유사도와 llm-reranking이 사용되는지?

## Question FD4-Q5 — 고증 confidence
생성된 고증 지식의 confidence는?

A) Wiki prior confidence × 감쇠계수(예: 0.8) — 추론임을 반영, 보강 검토 가능하게 (Recommended)
B) 1.0 고정
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — U4 입출력(KnowledgeGraph) + 스코핑/고증 규약
- [ ] `business-logic-model.md` — OntologyBuilder 흐름(그래프화·스코핑·고증·병합), Wiki 사용
- [ ] `business-rules.md` — 스코프/ABOUT/고증/병합 규칙·불변식

## Execution Checklist
- [x] 1. FD4-Q1~5 (+CL1=A 글로벌 지식, CL2=C 벡터+LLM dedup) 반영
- [x] 2. 산출물 3종 작성

---

## Follow-up (확인 필요)

### Question FD4-CL1 — 글로벌 지식 모델링 (Q1=X 반영)
지역에 매이지 않는 **세계 전역 지식**(예: "[world]는 해가 동쪽에서 뜬다")을 어떻게 표현할까요?

A) `Knowledge.is_global` 플래그 추가(U1 모델) + `ScopeType.GLOBAL` 추가. LLM이 각 지식의 scope(region|global)를 판정(ExtractedKnowledge에 `is_global` 추가). 글로벌 지식은 **모든 지역 쿼리에 포함**, SCOPED_TO 없음 (Recommended — 단순·쿼리 일관)
B) 별도 `:GlobalKnowledge` 노드 라벨로 분리
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question FD4-CL2 — 지식 중복 제거(dedup) 방식 (Q4 보충)
중복 판정에 의미 검색을 쓸까요?

A) 정규화 statement **exact 병합만** (MVP, 결정적·무비용) (Recommended for MVP)
B) exact + **벡터 유사도 near-dup 병합**(OpenSearch, 임계값) — LLM 리랭킹 없음 (의미 중복 일부 잡음, 결정적 임계)
C) **벡터 유사도 + LLM 리랭킹**(참고 Enola 방식) — 가장 정교, 비결정적·비용↑
X) Other (please describe after [Answer]: tag below)

[Answer]: C. 병합은 예민한 부분이라 이게 맞음.
