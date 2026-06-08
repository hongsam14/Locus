# U3 Topology — Business Logic Model

## TopologyBuilder.build(ingestion, world_id, wiki) -> RegionTopology

### 1. 지역 식별 + 계층 (US-2.1, FD3-Q1=A)
- regions = ingestion.region_hints (이미 U2에서 이름 병합됨).
- 이름→Region 인덱스 구성(normalize_name).
- 각 region의 `attributes["parent_name"]`로 부모 탐색 → 있으면 `parent_id` 설정(CONTAINS).
  - 부모 미지정/미발견 → 최상위(parent_id=None). 합성 루트 없음.
- 순환 방지: parent 체인에 자기 자신이 나오면 parent_id 무시(+경고).

### 2. 연결 엣지 (US-2.2, FD3-Q2=A)
연결 후보 수집:
- `connection_hints`(region.attributes에 보존된 U2 힌트) → {from,to,kind?}.
- terrain 엔티티(entity_type=terrain) 의 `between=[A,B]`(provenance.note 또는 별도 채널) → kind = terrain kind 매핑(mountain→blocked, river→river, road→route, …).
- from/to 이름을 region id로 해소(미해소 시 skip + 경고).
- 무방향 쌍 단위로 중복 제거(정렬된 (a,b) 키).

### 3. weight 가중 (US-2.3, FD3-Q3/Q4=A)
각 연결 쌍에 대해:
- base = BASE_WEIGHT[kind].
- 관련 terrain feature들에 대해 `wiki.lookup_terrain_rule(feature)` 호출 →
  - 수치 수정자는 `TERRAIN_MODIFIER[terrain_kind]` 휴리스틱 표 사용(결정적).
  - rationale = 매칭된 Wiki prior.effect(있으면) 누적; `wiki_prior_ref` = prior.id; DERIVED_FROM 근거.
- weight = clamp(base × Π(modifiers), 0, 1).
- 양방향 ConnectionEdge 2개 생성(provenance.source=inferred-wiki if wiki 기여, else input).

### 4. 출력
- RegionTopology(regions=계층반영 regions, connections=양방향 엣지들).
- (저장은 서비스/U9 PipelineOrchestrator가 GraphRepository로; U3는 빌더 + 순수 로직 제공.)

## 순수 함수 분리 (테스트)
- `assign_hierarchy(regions)` — parent_name→parent_id (Wiki/IO 무관).
- `collect_connection_candidates(regions, terrain)` — 후보 쌍+kind.
- `base_weight(kind)`, `terrain_modifier(kind)`, `compute_weight(base, terrain_kinds)`.
- Wiki 호출부만 mock 필요; 나머지는 순수.

## Wiki 사용
- `CommonsenseWiki`(U1) 주입. 빈 Wiki면 LLM 폴백(rationale만; 수치는 휴리스틱). 실패 시 base weight 사용(graceful).
