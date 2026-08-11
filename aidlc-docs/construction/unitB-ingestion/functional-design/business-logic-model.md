# Unit-B — Business Logic Model (Functional Design)

영역 4. case2=인제스터 Region 승격, case1=OntologyBuilder 교차소스 병합, 잔여=augmentation.

## 1. 인제스터: terrain 분류 & 승격 (case2, Q1=B/Q2=A/Q6=A)
`map_image_ingestor.extract`:
1. VLM 추출(MapExtraction) — terrain에 `x,y` 포함.
2. 각 terrain을 분류:
   - **barrier kind**(`_BARRIER_KINDS`) → 기존 동작: `between`(2개)로 A–B 연결 힌트 생성. (Entity 생성 안 함 — 더 이상 orphan terrain entity 없음.)
   - **면적형**(그 외) → `to_terrain_region(t)` = `Region(level=TERRAIN, position=Coord(x,y), attributes={terrain_kind, origin:"vlm"})`로 승격. region_hints에 추가.
3. 승격 terrain-Region의 연결성(VLM 추론):
   - `between`에 명시된 region들과 `adjacent` 연결 힌트 생성(terrain-Region ↔ 각 region).
   - `between` 없으면 위치 기반 인접은 OntologyBuilder/topology가 처리(또는 미연결 → augmentation).
4. 결과: `map_image` IngestionResult.entities는 비거나 거의 없음(terrain은 region으로 승격, barrier는 hint).

`concept_art_ingestor`: 기존대로 저신뢰 clue entity 생성(좌표 없음). 연결은 OntologyBuilder가 담당(Q4).

## 2. OntologyBuilder: 교차소스 병합 (case1, Q3=A)
신규 `EntityReconciler` 단계(OntologyBuilder.build 내, scoping/dedup 전후):
입력: 전체 entities(VLM+text+structured) + regions.
1. **fuzzy 후보**: 정규화 문자열 유사도(예: 토큰/Levenshtein)로 VLM-origin 노드마다 비-VLM 노드 후보 추림.
2. **임베딩 유사도**: 후보를 임베딩 코사인으로 정렬(EmbeddingProvider; 없으면 fuzzy만).
3. **LLM 최종 판정**: 상위 후보쌍을 `EntityMatchVerdict`로 동일 여부 판정.
4. **병합**: 동일 판정 시 **비-VLM 노드를 canonical**로, VLM 노드 흡수(id remap) 후 제거(Q3=A). RELATED_TO/about/located_in 등 참조를 canonical로 remap.
- VLM-origin 판정: `provenance.generated_by == "vlm"`.
- 가드(NFR-IM4): fuzzy/임베딩으로 후보 제한 후에만 LLM 호출.

## 3. orphan 연결 (Q4=A, FR-IM4.3/4.4)
병합 후에도 어떤 region/entity에도 연결 안 된 entity 처리:
1. **의미 매칭**: 기존 entity와 임베딩+LLM 매칭 → 동일하면 병합, 유관하면 `RELATED_TO`.
2. **지역 귀속**: 매칭 실패 시 가장 그럴듯한 region 선택(VLM entity는 position 근접 region; concept art는 임베딩/LLM) → `Entity.located_in` 설정 → `LOCATED_IN` 엣지.
3. **승격 terrain-Region 연결**: `between`/위치로 인접 region과 `CONNECTED_TO`(topology). 연결 못 하면 잔여.
4. **잔여 → augmentation 후보**(Q5=A): `KnowledgeGraph.unconnected_entity_ids`에 기록, 저신뢰 보존, 미연결 플래그. 드롭하지 않음.

## 4. LOCATED_IN 엣지 영속화 (핵심 갭 해소)
- `graph_mapping.located_in_edges(entities)` 신설 → `persist_graph`가 `LOCATED_IN` 엣지 upsert.
- text/structured/VLM 모든 entity 일관 적용(FR-IM4.4): `located_in` 채워지면 엣지 생성.

## 5. Topology: 승격 terrain-Region 편입
- terrain-Region은 region_hints에 포함되므로 `assign_hierarchy` + `collect_connection_candidates`가 자동 처리.
- terrain-Region의 `adjacent` 힌트로 `CONNECTED_TO` 생성. `_TERRAIN_TO_KIND`/weights는 기존 재사용.

## 6. Augmentation: orphan 표면화 (Q4/Q5)
- `detectors.detect_gaps`(또는 신규 `detect_orphans`) 확장: 엣지가 전혀 없는 entity/region을 issue로 surface. `unconnected_entity_ids`도 입력.
- 기존 Q&A 루프가 "이 항목을 어디에 연결?" 질문 생성(QuestionGenerator) → 사용자 답변으로 LOCATED_IN/RELATED_TO 생성(apply).

## 7. 처리 위치 요약 (Q14 재확인)
| 작업 | 위치 |
|---|---|
| terrain 면적형 → Region 승격 + barrier 힌트 (case2) | 인제스터(map_image) |
| 교차소스 이름-오추출 병합 (case1) | OntologyBuilder(EntityReconciler) |
| orphan 의미매칭/지역귀속 | OntologyBuilder |
| LOCATED_IN 엣지 생성 | graph_mapping + persist |
| 잔여 미연결 표면화·질의 | augmentation |
