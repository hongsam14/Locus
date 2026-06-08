# U6 Commonsense Wiki (build) — Business Rules

## 파티션
- BR-U6-1: U6의 모든 쓰기는 `world_id=__realworld__`. 가상 세계 파티션에 쓰지 않음.
- BR-U6-2: 가상 세계 빌드(U9)는 `__realworld__`에 쓰지 않음(역방향 격리).

## Prior
- BR-U6-3: distill된 WikiPrior는 `source=inferred-wiki`, `generated_by=llm`, provenance 필수(US-5.3).
- BR-U6-4: condition/effect 비어있는 prior는 거부(경고).
- BR-U6-5: confidence ∈ [0,1].

## 빌드/영속
- BR-U6-6: append(Q5=B) — 재빌드는 기존 `__realworld__` 삭제하지 않음.
- BR-U6-7: 색인 대상(knowledge/entity/wikiprior)은 text 비어있으면 색인 제외(U1 BR-18 일관).
- BR-U6-8: distill/embed/LLM 실패는 graceful — 해당 부분 생략 + WikiBuildReport.warnings, 빌드 미중단.

## 편집
- BR-U6-9: `upsert_prior`는 동일 id면 갱신, provenance 보존/갱신.

## 재사용/매핑
- BR-U6-10: WikiBuilder는 U2/U3/U4를 그대로 재사용(중복 구현 금지).
- BR-U6-11: graph_mapping(domain→Node/Edge/SearchDoc)은 순수 함수 → 단위 테스트, U9 재사용.
- BR-U6-12: 빌드 시 TopologyBuilder/OntologyBuilder에 wiki를 주입하지 않음(자기참조 방지).
