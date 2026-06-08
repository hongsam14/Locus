# U5 Consensus — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-4.1 (share/propagate/unknown), US-4.2 (hybrid static+query-time), US-4.3 (distortion: decay + rumor).
**Verification**: 73 tests PASS (67 prior + 6 U5, incl. PBT path-weight bound); ruff + black clean. Pure (no IO).

## Created files (`locus/consensus/`)
- `propagation.py` — `best_path_weights` (max-product Dijkstra over CONNECTED_TO). Pure.
- `engine.py` — `ConsensusParams` (propagate_min 0.5 / rumor_min 0.15), pure `compute_consensus`, `ConsensusEngine.resolve` (in-memory).
- `__init__.py` — re-exports.

## Modified files (additive)
- `locus/models/io.py` — `ConsensusView.global_knowledge`; `KnowledgeView.distortion_degree`.

## Created tests (`tests/consensus/test_consensus.py`)
max-product weights (roads spread further, +PBT bound, stronger-route preference), classification (direct/inherited/global/propagated/rumor + distortion=1−pw + decayed confidence), unknown below threshold, engine.resolve.

## Key realizations
- **Hybrid (Q3=C)**: direct scope read from stored ScopeLinks (static); propagation/rumor computed at query time via weighted reachability.
- **Roads vs cut-offs (user note)**: `path_weight = Π edge weight` (max-product) → high-weight routes propagate far; low-weight (mountain/sea) collapse → rumor/unknown.
- **Distortion (FR-D3)**: propagated = confidence × path_weight (decay only); rumor = `is_rumor` view + `distortion_degree = 1 − path_weight` (ephemeral, not persisted; Q2=A).
- **Global knowledge** included for every region (CL1=A); dedup priority direct > inherited > global > propagated > rumor.
- In-memory pure algorithm (Q4=A); repo loading deferred to U8/U9.

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U5 (inherits U1 + shared infra).
