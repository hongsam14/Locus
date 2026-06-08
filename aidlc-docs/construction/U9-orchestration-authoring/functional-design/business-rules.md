# U9 Orchestration & Authoring — Business Rules

## 빌드 순서 / 영속
- BR-U9-1: build_world 순서 = Ingestion → Topology(+Wiki) → Ontology → persist. (BR-U6-10 재사용.)
- BR-U9-2: 컨센서스(전파/소문)는 영속하지 않음 — 쿼리 시점 계산(FD9-Q1=A, FD1-Q3=C).
- BR-U9-3: persist는 graph_mapping(정매핑) 사용; 색인 대상만 OpenSearch.
- BR-U9-4: 각 단계 graceful — 실패는 BuildReport.warnings, 빌드 중단 최소화.

## 격리
- BR-U9-5: build_world는 주어진 world_id에만 씀. `__realworld__`에 쓰지 않음(그건 build_wiki).
- BR-U9-6: TopologyBuilder/OntologyBuilder에 주입되는 CommonsenseWiki는 `__realworld__` 읽기 전용.

## 편집 (Q2=C)
- BR-U9-7: upsert는 동일 id면 갱신(idempotent), provenance 보존.
- BR-U9-8: delete_node는 노드+연결 엣지 제거(DETACH) + 색인 삭제(가능 시). world_id 스코프.
- BR-U9-9: knowledge upsert/삭제 시 OpenSearch 색인 동기화.

## API / CLI
- BR-U9-10: authoring은 내부용(인증 MVP 없음, Security OFF) — serving과 라우터 분리(AD-Q6=A).
- BR-U9-11: 없는 리소스 → 404, 잘못된 본문 → 422, 저장소 오류 → 500.
- BR-U9-12: CLI 명령은 0(성공)/비0(실패) 종료코드, 결과 요약 출력.

## Export
- BR-U9-13: export는 world_id 스코프 전체 그래프를 JSON 직렬화(round-trip 가능 필드 보존).
