# U3 Topology — Code Generation Plan

Code 위치 = `locus/topology/`. U1 모델·Wiki 인터페이스 사용. Stories US-2.1~2.3.

## Steps  (ALL DONE — 48 tests pass, ruff/black clean)
- [x] **Step 1 — weights** (`locus/topology/weights.py`): `BASE_WEIGHT`, `TERRAIN_MODIFIER`, `base_weight(kind)`, `terrain_modifier(kind)`, `compute_weight(base, terrain_kinds)`(clamp). 순수.
- [ ] **Step 2 — hierarchy** (`locus/topology/hierarchy.py`): `assign_hierarchy(regions)` parent_name→parent_id, 비순환 가드. 순수.
- [ ] **Step 3 — TopologyBuilder** (`locus/topology/builder.py`): `collect_connection_candidates(regions, terrain)`(순수) + `build(ingestion, world_id, wiki)` (계층+엣지+Wiki 가중, 양방향, graceful).
- [ ] **Step 4 — `__init__.py`** 재노출.
- [ ] **Step 5 — Tests** (`tests/topology/`): weight 계산(+clamp, PBT 범위), hierarchy(부모 연결/고아/순환), connection candidates(hint+terrain, 미해소 skip), build with mock Wiki(가중·rationale·대칭).
- [ ] **Step 6 — Docs**: `construction/U3-topology/code/code-gen-summary.md`.

## Story Coverage
US-2.1→Step2 · US-2.2→Step3 · US-2.3→Step1,3.

## Notes
- Wiki(U1) 주입(mock). 순수 로직 LLM/IO 비의존. 생성 후 pytest 검증(오프라인).
