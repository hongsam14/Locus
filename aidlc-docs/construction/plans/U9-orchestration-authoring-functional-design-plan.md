# U9 Orchestration & Authoring — Functional Design Plan

U9는 MVP를 관통합니다: **PipelineOrchestrator**(자료→그래프 전체 빌드+영속), **authoring API**, **CLI**, **데모 샘플**. 기존 U2~U6/U8을 재사용해 end-to-end(SC-1/2/4)를 완성합니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD9-Q1 — build_world 흐름
가상 세계 빌드 파이프라인은?

A) Ingestion → Topology(+Wiki 가중) → Ontology(+스코핑/고증/dedup) → **persist**(graph_mapping → Neo4j/OpenSearch). 컨센서스는 쿼리 시점(U5)이라 영속 불필요. BuildReport 반환 (Recommended)
B) 위 + 컨센서스 결과까지 미리 계산·영속
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 그러면 컨센서스는 항상 실시간 계산?

## Question FD9-Q2 — authoring API 범위(MVP)
내부(기획자) authoring API에 무엇을 넣을까요?

A) `POST /api/authoring/worlds/{world_id}/build`(WorldInputs) + `POST /api/authoring/wiki/build` + `GET /api/authoring/worlds/{world_id}/graph`(요약 조회) + `POST /api/authoring/wiki/priors`(upsert) (Recommended — 빌드/조회/Wiki편집)
B) 빌드 엔드포인트만(조회/편집은 U10/U7)
C) 위 A + 노드/지식 편집(추가/수정/삭제)까지
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question FD9-Q3 — CLI 명령
CLI(`locus`)에 추가할 명령은?

A) `build-world`(inputs→빌드) + `build-wiki`(번들/사용자) + `export`(world→JSON) + 기존 `init-schema` (Recommended)
B) build-world / build-wiki 만
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD9-Q4 — Export 형식
`export`(US-9 보조, NPC 런타임 정적 번들)는?

A) world 전체 그래프를 JSON으로(regions/entities/knowledge/scopes/connections) 파일 출력 (Recommended — 간단·이식)
B) 지역별 쿼리 결과(QueryResult) 번들로 사전 계산 출력
C) 둘 다
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD9-Q5 — 데모 가상 세계 샘플(Q12=C)
SC 검증용 데모 세계는?

A) 작은 가상 세계 샘플(메모+간단 맵) 번들 동봉 + 로더 → `build-world`로 즉시 end-to-end 검증 (Recommended)
B) 동봉 안 함(사용자 제공만)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — build_world 입출력 + persist 규약(graph_mapping 재사용)
- [ ] `business-logic-model.md` — PipelineOrchestrator, authoring router, CLI, app 통합, 데모
- [ ] `business-rules.md` — 빌드 순서·영속·격리·오류 처리 규칙

## Execution Checklist
- [x] 1. FD9-Q1~5 반영 (Q2=C 편집 포함; 컨센서스 실시간 확인)
- [x] 2. 산출물 3종 작성
