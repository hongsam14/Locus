# U5 Consensus — Domain Entities & Parameters

U5는 U1 모델만 사용(신규 노드 없음). 결정: FD5 전부 A. 소문은 ephemeral view(미영속).

## Input → Output
- Input(in-memory, FD5-Q4=A): `RegionTopology`(regions+connections) + `KnowledgeGraph`(knowledge+scopes). 로딩은 U8/U9.
- Output: `ConsensusView { world_id, region_id, direct[], inherited[], propagated[], rumors[], unknown_count }` (U1 모델, 항목=`KnowledgeView`).

## Parameters (기본값, 조정 가능)
| 이름 | 값 | 의미 |
|---|---|---|
| PROPAGATE_MIN | 0.5 | path_weight ≥ → propagated |
| RUMOR_MIN | 0.15 | RUMOR_MIN ≤ path_weight < PROPAGATE_MIN → rumor |
| (else) | <0.15 | unknown(count만) |

## 핵심 의미 (Q1 노트 반영)
- path_weight = 시작 지역→대상 지역 경로의 CONNECTED_TO weight **곱** (max-product 경로).
- 도로(weight↑) → path_weight 유지 → 멀리까지 propagated. 산맥/단절(weight↓) → 급감 → rumor/unknown.
- 도달 confidence = `knowledge.confidence × path_weight`.
- **distortion_degree = 1 − path_weight** (접근 어려울수록 왜곡↑). rumor view에 기록.

## KnowledgeView 분류
- direct: 해당 지역 SCOPED_TO(direct).
- inherited: CONTAINS 조상의 direct (scope_type=inherited).
- global: is_global 지식(모든 지역).
- propagated: 타 지역 direct가 path_weight≥PROPAGATE_MIN로 도달(confidence 감쇠).
- rumors: RUMOR_MIN≤path_weight<PROPAGATE_MIN (is_rumor=true, distortion_degree).
- 중복 제거: 동일 knowledge는 가장 강한 분류 1회만(direct>inherited>global>propagated>rumor 우선; 또는 최대 path_weight).
