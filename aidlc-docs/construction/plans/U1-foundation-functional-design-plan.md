# U1 Foundation — Functional Design Plan

U1은 공유 토대(도메인 모델 + **그래프 스키마** + Storage/LLM/Wiki 인터페이스)입니다. 그래프 스키마는 이후 모든 Unit의 계약이므로 여기서 핵심 모델링을 확정합니다. 기술 무관(technology-agnostic) 설계이며, 저장소 구현 세부는 NFR/Infra에서 다룹니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD1-Q1 — 다중 세계(world) + Wiki 격리 방식
여러 게임 세계와 실세계 Wiki를 어떻게 분리할까요?

A) `world_id` 속성 파티션 — 단일 그래프에 모든 노드가 `world_id`를 갖고, Wiki는 예약 id(예: `__realworld__`) (Recommended — 단순, 교차 참조·비교 쉬움)
B) Neo4j database/네임스페이스 분리 — 세계별 별도 DB
C) 완전 별도 저장 인스턴스
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD1-Q2 — 노드 식별자 전략
노드 ID는?

A) UUID(불변) + `(world_id, type, natural_key)` 유니크 제약 (Recommended — 안정적 참조 + 중복 방지)
B) 자연 키만 (`world_id`+이름) — 단순하나 개명 시 취약
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD1-Q3 — 지식의 지역 스코핑 표현
KnowledgeItem이 지역에 귀속되는 방식은?

A) `(:Knowledge)-[:SCOPED_TO]->(:Region)` 관계 + 계층 상속은 Region `:CONTAINS` 트리 순회로 계산 (Recommended — 유연, 상속 동적)
B) 각 Knowledge에 region_id 배열 속성(상속을 빌드시 평탄화 저장)
C) 둘 다(관계 + 평탄화 캐시)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD1-Q4 — 왜곡/소문(variant) 모델링
FR-D3(confidence + variant)을 스키마로?

A) variant도 `:Knowledge` 노드(`is_variant=true`) + `(:Knowledge)-[:DISTORTED_FROM]->(:Knowledge)`; confidence는 지역-지식 관계( `SCOPED_TO`/전파 엣지)의 속성 (Recommended — 동일 타입 재사용, 쿼리 일관)
B) 별도 `:Rumor` 노드 라벨로 분리
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question FD1-Q5 — 의미 검색(OpenSearch) 색인 대상
어떤 객체를 임베딩·색인할까요? (CL6 하이브리드 검색)

A) Knowledge + Entity + WikiPrior (이름/설명 텍스트) (Recommended — 엔티티↔Wiki 매칭 + 유사 지식·고증 검색 모두 지원)
B) Knowledge만
C) Knowledge + WikiPrior
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD1-Q6 — 핵심 속성 표준
공통 수치/메타 표준에 동의하시나요? (confidence 0.0~1.0 float / connection weight 0.0~1.0 / 모든 생성 항목에 `source`(input|inferred-wiki|augmentation) + `provenance` 기록)

A) 동의 (Recommended)
B) 일부 변경 (X에 기재)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — 노드/관계/속성 그래프 스키마 + Pydantic 모델 목록
- [ ] `business-logic-model.md` — U1 범위 핵심 로직(임베딩 생성, repository 계약, wiki lookup 폴백 흐름)
- [ ] `business-rules.md` — 검증·제약·불변식(유니크, confidence 범위, provenance 필수 등)

## Execution Checklist
- [x] 1. FD1-Q1~6 반영해 스키마 확정 (Q4=B: 별도 :Rumor 라벨)
- [x] 2. domain-entities.md 작성
- [x] 3. business-logic-model.md 작성
- [x] 4. business-rules.md 작성
