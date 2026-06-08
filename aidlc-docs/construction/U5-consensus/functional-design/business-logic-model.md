# U5 Consensus — Business Logic Model

## 순수 핵심: compute_consensus(...) (FD5-Q4=A)
시그니처(개념):
```
compute_consensus(region_id, *, regions, connections, scopes, knowledge_by_id, params) -> ConsensusView
```
단계:
1. **인덱스**: region by id; CONTAINS 조상 경로; SCOPED_TO direct: region_id→[knowledge_id]; global = [k for k in knowledge if is_global].
2. **direct**: region_id의 direct knowledge → KnowledgeView(scope_type=direct, confidence=scope.confidence).
3. **inherited**: 조상들의 direct → KnowledgeView(inherited). (direct에 이미 있으면 제외.)
4. **global**: is_global → KnowledgeView(scope_type=global). (중복 제외.)
5. **전파(max-product BFS/Dijkstra)**: 시작 region에서 CONNECTED_TO weight 곱이 최대가 되는 경로의 path_weight를 지역별로 계산. 자기 지역=1.0.
   - 각 타 지역 r'의 direct knowledge k → eff = k.confidence × pw(r').
   - pw ≥ PROPAGATE_MIN → propagated(confidence=eff).
   - RUMOR_MIN ≤ pw < PROPAGATE_MIN → rumors(is_rumor, confidence=eff, distortion_degree=1−pw).
   - pw < RUMOR_MIN → unknown_count++.
   - 이미 direct/inherited/global인 knowledge는 전파에서 제외. 같은 knowledge 다중 경로는 최대 pw 채택.
6. ConsensusView 반환.

순수(LLM/IO 무관) → 단위 테스트/PBT.

## ConsensusEngine (FD5-Q5=A)
- `ConsensusEngine(knowledge_graph, topology, params=DEFAULT)` — 생성 시 인덱스 precompute(direct 맵, 조상, 인접/weight).
- `resolve(region_id) -> ConsensusView` — precompute된 인덱스로 compute_consensus 호출.
- `precompute()` — 인덱스 구성(직접=정적). 별도 영속 캐시 없음(MVP).

## PropagationResolver
- compute_consensus의 전파 부분을 담당하는 내부 헬퍼(max-product 경로 계산 `best_path_weights(region_id, regions, connections)` 순수).

## 데이터 로딩
- U5는 in-memory 입력만 받음. 실제 Neo4j/OpenSearch 적재(전 세계 서브그래프 → KnowledgeGraph+RegionTopology 복원)는 U8/U9가 제공(차후 graph_repo 조회).

## 왜곡(FR-D3)
- 경미(전파, pw 높음) → confidence 감쇠만.
- 변형(rumor, pw 낮음) → is_rumor view + distortion_degree=1−pw. (영속 :Rumor 노드는 차순/authored 전용.)
