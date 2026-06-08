# U8 Query & Serving API — Functional Design Plan

U8는 "지역 X NPC가 아는 지식" 조회와 공유/고유 구분을 제공하고(FR-H, US-8.1~8.3), 공개 **serving REST API**로 노출합니다. U5 ConsensusEngine을 사용하며, 저장소(Neo4j)에서 세계를 메모리로 적재해 계산합니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD8-Q1 — 세계 적재(load) 방식
U5는 in-memory 계산이므로, 저장된 세계를 어떻게 불러올까요?

A) **WorldLoader** — GraphRepository에서 노드/엣지를 읽어 KnowledgeGraph+RegionTopology로 **역매핑(reverse graph_mapping)** 복원 → ConsensusEngine 실행. (GraphRepository에 `get_edges(world_id)` 추가) (Recommended — U5 순수 엔진 재사용, 소규모 NFR 적합)
B) 컨센서스를 Cypher로 직접 계산(엔진 미사용)
C) 빌드시 KnowledgeGraph+Topology 스냅샷(JSON) 저장→조회 시 로드(Neo4j 우회)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD8-Q2 — 쿼리 API 엔드포인트
공개 serving API 구성은?

A) `GET /api/query/regions/{region_id}/knowledge?include_rumors=&world_id=` + `GET /api/query/diff?region_a=&region_b=&world_id=` (Recommended — US-8.1/8.2)
B) 하나의 엔드포인트로 통합
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD8-Q3 — 단일 지역 공유/고유 구분 의미
QueryResult의 shared_ids / unique_ids 정의는?

A) **unique = direct(그 지역 고유)**; **shared = inherited+global+propagated+rumors(다른 곳에서 옴/공통)** (Recommended — NPC의 고유 로어 vs 공통 지식 구분)
B) 단일 지역에선 구분 안 함(diff에서만)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD8-Q4 — 소문 포함 + 메타데이터
응답에 무엇을 담을까요?

A) 각 항목에 scope_type, is_rumor, distortion_degree, confidence, source, region_id 포함 + `include_rumors`(기본 true) (Recommended — US-8.3)
B) 최소(문장+confidence)만
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD8-Q5 — serving 인증
공개 쿼리 API 인증은?

A) 없음(로컬/내부, Security 확장 OFF) (Recommended for MVP)
B) API 키 헤더
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — QueryResult/RegionDiff 계약 + API 스키마 + 역매핑 규약
- [ ] `business-logic-model.md` — WorldLoader, QueryEngine(knowledge_for_region/diff_regions), serving router
- [ ] `business-rules.md` — 공유/고유 규칙, 적재·역매핑, 오류 처리

## Execution Checklist
- [x] 1. FD8-Q1~5 반영 (all A)
- [x] 2. 산출물 3종 작성
