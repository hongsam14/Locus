# Phase 2 — Performance Notes (light)

> Phase 2 is a local single-operator authoring/play-through tool; no formal load SLA. Notes for awareness.

## Characteristics
- **advance_turn cost** = O(active events × regions) for distortion (pure, in-memory) + O(active-event regions) rumor generation (LLM calls, the dominant latency) + O(rumors) support evolution + O(rumors) promotion. LLM calls in rumor append are the bottleneck; deterministic steps are negligible.
- **propagate_delta** reuses `best_path_weights` (Dijkstra-like max-product) per event — O(E log V).
- **suggest_events** = 1 LLM call (graceful timeout → []).

## Guidance
- Rumor count **grows each turn** (FD-P2 Q5=A append) — for long sessions, use manual `regenerate_region` (wipe) to bound growth, or resolve/limit active events.
- DB: session tables are modest; `session_events`/`session_rumors` indexed by `session_id`/`region_id`/`status`.

## If latency matters
- Reduce active events per turn; lower suggest `n`; cap rumor chain. No code SLA enforced this cycle.
