# U8 Query & Serving — Business Rules

## 공유 / 고유 (FD8-Q3=A, SC-2)
- BR-U8-1: 단일 지역 unique_ids = direct 항목 id; shared_ids = inherited+global+propagated+rumors 항목 id.
- BR-U8-2: include_rumors=false면 rumors 제외(items·shared 모두에서).
- BR-U8-3: diff_regions: shared = a·b 공통 knowledge_id, only_a/only_b = 차집합 (rumors 포함 여부는 동일 플래그 적용).

## 적재 / 역매핑 (FD8-Q1=A)
- BR-U8-4: WorldLoader는 world_id 스코프 노드/엣지만 적재(누출 금지).
- BR-U8-5: 역매핑은 graph_mapping의 정매핑과 round-trip 호환(핵심 필드 보존: id/world_id/confidence/is_global/scope_type/weight).
- BR-U8-6: 알 수 없는 라벨/엣지 타입은 무시(경고 가능).

## API
- BR-U8-7: 없는 region_id → 404; 누락 필수 파라미터 → 400; 저장소 오류 → 500(메시지 최소).
- BR-U8-8: 응답은 JSON(QueryResult/RegionDiff). 결정적 계약(필드 안정, 소비자=NPC 런타임).
- BR-U8-9: 인증 없음(MVP, Security OFF) — 단, world_id 스코프 격리는 유지.

## 결정성/테스트
- BR-U8-10: split_shared_unique/diff_sets 순수 → 단위 테스트. Loader/Engine/HTTP는 mock.
