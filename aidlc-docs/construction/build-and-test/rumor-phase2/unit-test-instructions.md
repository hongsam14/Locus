# Phase 2 — Unit Test Execution

## Backend
```bash
pip install -e ".[dev]"
pytest                       # full suite
ruff check locus api tests && black --check locus api tests
python -m compileall locus api
```
- **Expected**: **219 passed**, 0 fail, ~85% coverage. ruff/black/compileall clean.
- Phase 2 unit tests:
  - `tests/session/test_events.py` (P1) — SessionEvent model/enums/default_lifecycle, create/list/resolve(state)/discard, region validation, closed-session guards.
  - `tests/session/test_dynamics.py` (P2, **PBT/hypothesis**) — distortion_delta range/monotone, propagate threshold/decay, apply↔restore symmetry, evolve_support sign/range, merge_add.
  - `tests/session/test_advance_turn.py` (P2) — advance_turn integration, persistent accumulation + resolve restore, one_shot auto-resolve, rumor append, support evolution, suggest/approve, graceful LLM.
  - `tests/session/test_repository_contract.py` + `tests/storage/test_postgres_session_repo.py` — Event CRUD (in-memory + SQLite-backed Postgres adapter).
  - `tests/session/test_session_api.py` — event routes, suggest/approve, distortions.

## Frontend
```bash
cd web && npm test          # vitest
npx tsc --noEmit && npm run build
```
- **Expected**: **17 passed** (5 pure + 12 component). tsc/vite clean.
- Phase 2: SessionPanel event create form, suggest/approve/resolve, real distortion, closed-session disabled (`components.test.tsx`).

## On failure
Review output, fix code, rerun until green. Postgres adapter is exercised offline via SQLite (live PG operator-run, see integration).
