# U3 Topology — Domain Entities & Weight Model

U3는 U1 모델만 사용(신규 노드 타입 없음). 결정: FD3 전부 A.

## Input → Output
- Input: `IngestionResult`(region_hints[], entities[](terrain 포함), errors) — U2 산출.
- Output: `RegionTopology { world_id, regions[], connections[] }` (U1 모델).
  - regions: 계층(parent_id 채움) 반영된 `Region`.
  - connections: `ConnectionEdge`(kind, weight, rationale, wiki_prior_ref, provenance).

## 연결 kind 기본 weight (FD3-Q3=A)
| kind | base weight |
|---|---|
| adjacent | 0.8 |
| route | 0.6 |
| river | 0.5 |
| blocked | 0.2 |

## 지형 kind → Wiki 수정자 휴리스틱 (FD3-Q4=A)
| terrain kind | weight ×modifier | 의미 |
|---|---|---|
| mountain / range | ×0.4 | 교류 지연 |
| desert | ×0.5 | 통행 곤란 |
| river | ×0.8 | 도하 가능, 약간 저하 |
| sea / ocean | ×0.3 | 큰 단절 |
| road / route / bridge | ×1.2 (상한 1.0) | 교류 촉진 |
| (기타) | ×1.0 | 영향 없음 |

- 최종 `weight = clamp(base × Π(modifiers), 0.0, 1.0)`.
- terrain.between=[A,B]가 있으면 A-B 엣지에 해당 kind 수정자 적용.
- Wiki `lookup_terrain_rule(feature)` 호출 → 매칭 prior가 있으면 `rationale`에 prior.effect 기록 + `wiki_prior_ref`/`DERIVED_FROM`(가중 근거). 수치는 휴리스틱 표 사용(결정적).

## 방향성 (FD3-Q5=A)
- 각 무방향 연결마다 **양방향 ConnectionEdge 2개**(A→B, B→A) 생성(동일 weight/kind).
