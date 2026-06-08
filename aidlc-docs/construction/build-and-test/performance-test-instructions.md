# Performance Test Instructions — Locus

## Scope
NFR1-Q3 = **best-effort, no hard targets** (MVP). Performance testing is therefore light/optional; this documents how to sanity-check, not a gate.

## Characteristics
- **Build** (`build-world`): batch, dominated by LLM/VLM latency (ingestion extraction + corroboration + dedup judging). Wall-clock scales with input size × model latency. No SLA.
- **Query** (`/api/query/...`): loads the world subgraph in-memory (WorldLoader) then computes consensus (max-product BFS). For small worlds (regions ~10²) this is sub-second; cost grows with world size since there is **no consensus cache** (ND1-Q3=B).

## Optional sanity checks
```bash
# 1. Build time for the demo world
time locus build-world --world aldermoor --demo
# 2. Query latency (after API up)
time curl "localhost:8000/api/query/regions/<id>/knowledge?world_id=aldermoor"
```
- **Observe**: build completes in minutes (LLM-bound); query responds well under 1s at demo scale.

## When to optimize (future)
- If query latency grows: add per-region consensus cache (precompute) + invalidate on build/edit; cache WorldLoader results.
- If build is slow: batch/parallelize LLM calls; cache embeddings (currently none, ND1-Q3=B).

## Status
- No performance gate for MVP. Recorded as **N/A (best-effort)** in the summary.
