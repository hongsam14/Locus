# Phase 2 — Integration Test Instructions

> Offline integration is covered by `test_advance_turn.py` + `test_session_api.py` (units wired through GameMasterService + FastAPI TestClient + in-memory/SQLite). The scenarios below are **live** (operator-run): real PostgreSQL + real LLM + web UI.

## Setup
```bash
cp env.example .env   # set NEO4J_PASSWORD, SESSION_DB_PASSWORD
docker compose up -d neo4j opensearch postgres
locus init-schema && locus build-world --world demo --demo
uvicorn api.main:app --port 8000
cd web && npm run dev
export S=http://localhost:8000/api/session
```

## Scenarios (P1+P2+P3 across units)
- **P2-A (event → dynamic distortion + propagation)**: start session; `POST $S/sessions/{sid}/events` (war, magnitude 1.0, persistent) on region R; `POST …/advance-turn`; `GET …/distortions` → R rose (+0.3) and topology neighbours rose by decayed delta. ✅ if target+neighbour distortion increased.
- **P2-B (persistent accumulation + resolve restore)**: advance 2–3 turns → R distortion accumulates (clamp ≤1.0); `POST …/events/{eid}/resolve` → distortion restored toward pre-event baseline (target + neighbours symmetric).
- **P2-C (one_shot)**: create disaster (one_shot); advance once → applied + status=resolved (no further per-turn effect).
- **P2-D (LLM suggest → approve, live LLM)**: `POST …/suggest-events?n=2` → SUGGESTED events persisted; `POST …/events/{eid}/approve` → ACTIVE; next advance-turn applies. LLM down → `[]` (graceful), turn still advances.
- **P2-E (support auto-evolution + promotion)**: generate rumors; advance turns with an event on R → R rumors' support rises (+0.1), non-influenced regions decay (−0.05); crossing 0.6 → auto-promote (timeline PROMOTE); dropping below → demote.
- **P2-F (rumor append preserve)**: generate rumors in R; create event; advance → existing rumors + support preserved, new rumors appended.
- **P2-G (guards)**: close session → event writes (create/suggest/approve/resolve) return 409; reads (events/distortions/timeline) still 200.
- **P3-H (web UI end-to-end)**: SessionBar create/select session; SessionPanel: create event form, "Suggest events" → approve/discard, active event Resolve, distortion slider shows real value, Advance Turn, Timeline shows EVENT_*/PROMOTE entries.

## Cleanup
```bash
docker compose down            # volumes persist under ./data
```
