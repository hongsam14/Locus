# U6 Commonsense Wiki (build) — Functional Design Plan

U6는 **실세계 자료(지도·텍스트)를 입력받아 상식 Wiki(prior KB, 디지털 트윈)를 구성·저장·색인**하고, 편집·근거를 제공합니다(FR-E, FR-A6, US-1.5/5.1~5.3). U1의 `CommonsenseWiki` lookup이 이 데이터를 찾습니다. 빌드는 U2/U3/U4 파이프라인을 재사용합니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD6-Q1 — Wiki 저장 표현(핵심)
실세계 prior를 어떤 형태로 저장하고 lookup이 무엇을 검색할까요?

A) **WikiPrior 중심** — 실세계 자료를 ingest해 `WikiPrior`(condition/effect/fact) 레코드로 변환·저장·색인. lookup은 WikiPrior 검색(U1 인터페이스 그대로). 디지털 트윈 KG 전체 저장은 차순. (단순·인터페이스 일관, MVP)
B) **디지털 트윈 KG + 파생 WikiPrior** — 실세계 자료를 동일 파이프라인(U2→U3→U4)으로 `__realworld__` 파티션에 regions/entities/knowledge로 구성 + 거기서 WikiPrior 규칙 파생·색인. (CL2 비전 충실, 무거움)
C) 둘 다 저장하고 lookup은 WikiPrior + 실세계 knowledge 모두 검색
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question FD6-Q2 — 실세계 입력 소스
prior 구성용 실세계 자료는?

A) **기획자가 제공** — `WorldInputs`(메모·지도·구조화맵)을 `build_wiki`로 전달(가상 세계와 동일 수집기 재사용) (Recommended — CL2 부합, 재사용)
B) 번들 큐레이션 데이터셋 동봉
C) 둘 다(기본 번들 + 사용자 추가)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question FD6-Q3 — WikiPrior 도출(distillation) 방식
ingest된 실세계 자료 → condition→effect prior 변환은?

A) **LLM distillation(structured)** — 실세계 텍스트/지형에서 일반 규칙(예: 산맥→교류 지연) + 사실 prior 추출 (Recommended)
B) 직접 매핑 — 실세계 knowledge statement를 그대로 fact prior로(규칙화 없음)
C) 둘 다(규칙은 LLM, 사실은 직접)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD6-Q4 — 저장·색인·편집
WikiPrior 영속/검색/편집은?

A) `__realworld__` 파티션 Neo4j 저장 + OpenSearch 색인(U1 lookup 동작) + upsert 편집(US-5.2) + provenance 근거(US-5.3) (Recommended)
B) 색인 없이 Neo4j만(검색은 그래프 쿼리)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD6-Q5 — 재빌드 정책
같은 소스로 다시 빌드하면?

A) **교체(replace)** — `__realworld__` prior를 비우고 재구성(idempotent 결과) (Recommended)
B) 누적(append) — 기존에 추가
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — U6 입출력 + distillation 스키마
- [ ] `business-logic-model.md` — WikiBuilder 흐름(ingest 재사용·distill·저장·색인·편집)
- [ ] `business-rules.md` — 파티션·prior 검증·재빌드·provenance 규칙

## Execution Checklist
- [x] 1. FD6-Q1~5 반영 (Q1=B 디지털트윈+파생, Q2=C, Q3=A, Q4=A, Q5=B append)
- [x] 2. 산출물 3종 작성
