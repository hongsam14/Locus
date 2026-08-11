# Unit-B — Domain Entities (Functional Design)

영역 4: VLM entity orphan 해소. 확정 답: Q1=B(유형별 분기) / Q2=A(RegionLevel.TERRAIN) / Q3=A(fuzzy→임베딩→LLM, 비-VLM 승자) / Q4=A+Q&A / Q5=A(augmentation 후보) / Q6=A(terrain 좌표).

## 1. `RegionLevel`에 `TERRAIN` 추가 (Q2=A)
```
CONTINENT, PROVINCE, TOWN, DISTRICT, TERRAIN   # TERRAIN 신규
```
- 승격된 지형(면적형 terrain)은 `Region(level=TERRAIN)`. 거주 구역과 구분.
- consensus/계층에서 별도 취급 가능(예: TERRAIN region은 CONTAINS 계층의 잎이거나 독립).

## 2. `ExtractedTerrain`에 좌표 추가 (Q6=A)
```
ExtractedTerrain:
  name, kind, between[], note, confidence   # 기존
  x: float | None       # 신규 — VLM 추정 정규화 위치
  y: float | None        # 신규
```

## 3. 승격된 terrain-Region 표현 (Q1=B)
- **면적형 지형**(barrier kind 아님) → `Region(level=TERRAIN, position=Coord(x,y), attributes={terrain_kind, origin:"vlm"})`.
- **장벽/연결선 지형**(barrier kind) → 승격하지 않고 기존처럼 A–B 연결 힌트로만 사용.
- 분류 기준: `_BARRIER_KINDS = {mountain, mountains, range, sea, ocean, river, road, route, bridge}`. 그 외(plain/forest/valley/basin/desert/swamp/grassland/tundra/hills…)는 면적형 → 승격.

## 4. `LOCATED_IN` 엣지 신설 (핵심 갭)
현재 `Entity.located_in`은 **노드 속성으로만** 저장되고 그래프 엣지가 없음(매핑 부재). → orphan의 근본 원인 중 하나.
- `graph_mapping.located_in_edges(entities)` → `LOCATED_IN`(source=entity, target=region) 엣지 생성·영속화.
- `Entity.located_in`(기존 필드) 채워지면 엣지 생성.

## 5. orphan/미연결 추적 필드
- `IngestionResult`/`KnowledgeGraph`: 미연결 노드 id 추적(기존 `low_confidence_item_ids` 재사용 + 신규 의미 플래그). 설계상 `KnowledgeGraph`에 `unconnected_entity_ids: list[str]` 추가(augmentation 후보, Q5=A).
- Entity에 별도 `is_orphan` 필드는 추가하지 않음(엣지 부재로 판정; 미연결은 그래프에서 도출).

## 6. 신규 추출/판정 스키마 (LLM)
- `EntityMatchVerdict`(case1 병합 판정): `same_entity: bool`, `canonical_name: str | None`.
- (Q3=A 3단계의 LLM 최종 판정 단계용.)

## 7. 변경 없음(재사용)
- `Entity.located_in`(이미 존재), `Relation`/RELATED_TO, `Coord`, `merge_entities/merge_regions`(정확 일치 dedup) 그대로.
- 신규 노드 타입 없음(승격은 기존 Region 재사용). 신규 엣지는 `LOCATED_IN`뿐.

## 관계 요약 (Mermaid)
```mermaid
graph TD
  V["VLM terrain (area)"] -->|승격| TR["Region(level=TERRAIN, position)"]
  TR -->|CONNECTED_TO (between/인접)| R1["Region A"]
  E["VLM/concept entity"] -->|LOCATED_IN| R1
  E -->|RELATED_TO (case1 매칭)| E2["기존 entity (canonical)"]
  note["미연결 잔여 → unconnected_entity_ids → augmentation Q&A (Q5=A)"]
```
