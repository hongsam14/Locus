# Unit-B (Ingestion Connection) — Code Summary

영역 4: VLM entity orphan 해소. **124 tests GREEN, ruff/black 클린.**

## Created
- `locus/ontology/reconciler.py` — `EntityReconciler`: case1 교차소스 병합(fuzzy→임베딩→LLM, 비-VLM canonical) + orphan 연결(LOCATED_IN) + 잔여 `unconnected_entity_ids`. graceful(provider 없으면 미연결 보존).

## Modified
- `locus/models/enums.py` — `RegionLevel.TERRAIN`.
- `locus/models/io.py` — `KnowledgeGraph.unconnected_entity_ids`.
- `locus/ingestion/schemas.py` — `ExtractedTerrain.x/y`.
- `locus/ingestion/mapping.py` — `_BARRIER_KINDS`, `is_barrier_terrain()`, `to_terrain_region()`(Region level=TERRAIN, position, attributes).
- `locus/ingestion/map_image_ingestor.py` — terrain 분류: barrier→A–B 연결 힌트(엔티티 생성 안 함), 면적형→TERRAIN region 승격 + 인접 힌트. VLM terrain orphan 제거.
- `locus/storage/graph_mapping.py` — `located_in_edges()`(`LOCATED_IN` 엣지) 신설.
- `locus/storage/persistence.py` — `persist_graph` edges에 `located_in_edges` 포함.
- `locus/ontology/schemas.py` — `EntityMatchVerdict`, `RegionPickVerdict`.
- `locus/ontology/builder.py` — `OntologyBuilder.build`에 EntityReconciler 단계(entities/relations remap, located_in, unconnected_entity_ids; knowledge.about_entity_ids remap).
- `locus/augmentation/types.py` — `IssueType.ORPHAN`.
- `locus/augmentation/detectors.py` — `detect_orphans()` + `detect_all`에 포함.
- `locus/augmentation/questions.py` — ORPHAN 질문 템플릿.

## Tests
- `tests/ontology/test_reconciler.py`(신규) — 비-VLM canonical 병합, relation remap, orphan→region LOCATED_IN, provider 없을 때 미연결, 기연결 보존.
- `tests/ingestion/test_ingestion.py` — barrier=힌트/면적형=TERRAIN 승격으로 갱신(orphan terrain entity 0).
- `tests/commonsense_wiki/test_wiki_build.py` — `located_in_edges` 엣지 테스트.
- `tests/augmentation/test_augmentation.py` — `detect_orphans`.

## 처리 위치 (Q14 확정)
- case2 면적형 terrain→Region 승격 + barrier 힌트: **인제스터**(map_image).
- case1 이름-오추출 병합 + orphan 연결: **OntologyBuilder**(EntityReconciler).
- LOCATED_IN 엣지 영속화: graph_mapping/persistence.
- 미연결 잔여 표면화: **augmentation**(detect_orphans → Q&A).

## 불변식
- orphan 처리: 매칭→LOCATED_IN→`unconnected_entity_ids`(보존, 드롭 없음, BR-B8).
- LLM/임베딩 모든 단계 graceful(BR-B10). 후보 가드로 전수 LLM 호출 방지(BR-B7).
