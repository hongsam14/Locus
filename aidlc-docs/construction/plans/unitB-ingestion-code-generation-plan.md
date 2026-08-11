# Unit-B (Ingestion Connection) — Code Generation Plan

**Single source of truth.** Brownfield: 기존 파일 수정(복사본 금지).
설계: `construction/unitB-ingestion/functional-design/`. 영역 4: VLM entity orphan 해소.

## Unit Context
- **의존성**: Unit-A 완료(모델/매핑/그래프). 같은 코드베이스 위 증분.
- **핵심 갭**: `LOCATED_IN` 엣지 부재 → 신설. terrain orphan → 면적형 Region 승격.
- **불변식**: orphan 제로 지향(BR-B8, 드롭 없음), NPC 단일 world(Unit-A BR-A9 유지), graceful.

---

## 코드 생성 단계

### 그룹 1 — 모델 & 스키마
- [x] **Step 1: `locus/models/enums.py`** — `RegionLevel.TERRAIN` 추가.
- [x] **Step 2: `locus/models/io.py`** — `KnowledgeGraph.unconnected_entity_ids: list[str]`(augmentation 후보, BR-B8).
- [x] **Step 3: `locus/ingestion/schemas.py`** — `ExtractedTerrain.x/y: float | None` 추가.

### 그룹 2 — Repository: LOCATED_IN 엣지
- [x] **Step 4: `locus/storage/graph_mapping.py`** — `located_in_edges(entities)` 신설(type=`LOCATED_IN`, source=entity.id, target=entity.located_in; located_in 있을 때만).
- [x] **Step 5: `locus/storage/persistence.py`** — `persist_graph` edges에 `located_in_edges(entities)` 포함.
- [x] **Step 6: `locus/storage/neo4j_repo.py`** — `LOCATED_IN` 엣지 타입 지원 확인(일반 upsert_edges로 충분; 필요시 무변경).

### 그룹 3 — 인제스터: terrain 분류 & 승격 (case2)
- [x] **Step 7: `locus/ingestion/mapping.py`** — `_BARRIER_KINDS` 집합 + `is_barrier_terrain(kind)` + `to_terrain_region(t, world_id)`(Region level=TERRAIN, position=Coord(x,y), attributes{terrain_kind, origin:"vlm"}).
- [x] **Step 8: `locus/ingestion/map_image_ingestor.py`** — terrain 분류: barrier kind → 기존 A–B 연결 힌트(Entity 생성 안 함); 면적형 → terrain-Region 승격(region_hints에 추가) + `between` 기반 `adjacent` 연결 힌트(VLM 연결성). entities는 비-terrain만(거의 비움).

### 그룹 4 — OntologyBuilder: 교차소스 병합 + orphan 연결 (case1, Q3/Q4)
- [x] **Step 9: `locus/ontology/schemas.py`** — `EntityMatchVerdict(same_entity: bool, canonical_name: str | None)`.
- [x] **Step 10: `locus/ontology/reconciler.py`(신규) `EntityReconciler`** —
  - `_fuzzy_candidates`(정규화 문자열 유사도; 순수) → 임베딩 코사인 정렬(`similarity.cosine`) → LLM `EntityMatchVerdict` 판정(BR-B6/B7).
  - 병합: 비-VLM canonical, VLM 흡수·id remap·삭제. about_entity_ids/relations/located_in remap.
  - orphan 연결(BR-B8): 미연결 entity → 의미매칭(RELATED_TO) → 위치/임베딩 기반 region `LOCATED_IN` → 잔여는 `unconnected_entity_ids`.
  - graceful: provider 없으면 fuzzy/위치만; 실패 시 잔여.
- [x] **Step 11: `locus/ontology/builder.py`** — `OntologyBuilder.build`에 EntityReconciler 단계 통합(entities/relations remap, located_in 설정, unconnected_entity_ids를 KnowledgeGraph에 채움). 임베딩/LLM 주입(이미 보유).

### 그룹 5 — Augmentation: orphan 표면화 (Q4/Q5)
- [x] **Step 12: `locus/augmentation/types.py`** — `IssueType.ORPHAN = "orphan"` 추가.
- [x] **Step 13: `locus/augmentation/detectors.py`** — `detect_orphans(kg)`(엣지 없는 entity: located_in 없음 & RELATED_TO 없음 & about 대상 아님; + `unconnected_entity_ids`) → ORPHAN issue. `detect_all`에 포함.
- [x] **Step 14: `locus/augmentation/questions.py`** — ORPHAN용 질문 템플릿("이 항목을 어느 region/entity에 연결?") 추가(있으면 재사용).

### 그룹 6 — 테스트
- [x] **Step 15: 모델/매핑/저장 테스트** — RegionLevel.TERRAIN, ExtractedTerrain x/y, `to_terrain_region`, `located_in_edges`(엣지 생성), persistence에 LOCATED_IN 포함.
- [x] **Step 16: 인제스터 테스트** — `tests/ingestion/*`: barrier terrain→힌트(승격 안 함)·면적형→TERRAIN region 승격(position/attrs)·entities에 terrain orphan 없음.
- [x] **Step 17: reconciler 테스트** — `tests/ontology/*`: fuzzy→임베딩→LLM 병합(비-VLM canonical, VLM 흡수)·orphan 의미매칭/LOCATED_IN·잔여 unconnected_entity_ids·provider 없을 때 graceful.
- [x] **Step 18: augmentation 테스트** — `detect_orphans` issue·질문 생성.
- [x] **Step 19: 회귀** — 전체 pytest GREEN, ruff/black 클린. VLM 경로 e2e(mock)에서 orphan 0 확인.

### 그룹 7 — 문서
- [x] **Step 20: 코드 요약** — `aidlc-docs/construction/unitB-ingestion/code/code-summary.md`(modified/created). README/CLAUDE 필요 시 갱신.

---

## Story Traceability (FR-IM4)
- FR-IM4.1(case2 Region 승격, 인제스터) → Step 1,3,7,8
- FR-IM4.2(case1 병합, OntologyBuilder) → Step 9,10,11
- FR-IM4.3(orphan 제로/augmentation) → Step 2,10,12,13,14
- FR-IM4.4(LOCATED_IN 일관) → Step 4,5,6,10,11
- 총 20 스텝.
