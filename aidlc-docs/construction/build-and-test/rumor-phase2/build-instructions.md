# Phase 2 — Build Instructions

## Prerequisites
- **Python** 3.11+ · **Node** 18+/npm · Docker Compose (live use).
- **Deps**: backend `pip install -e ".[dev]"` (adds sqlalchemy>=2, psycopg[binary]>=3, hypothesis, ruff, black, pytest); frontend `cd web && npm install`.
- **Env**: `cp env.example .env`; set `NEO4J_PASSWORD`, `SESSION_DB_PASSWORD` (no insecure defaults). Phase 2 adds **no new env vars** (reuses `SESSION_DB_URL`).

## Build Steps
### 1. Backend (no compile; import + schema)
```bash
pip install -e ".[dev]"
python -m compileall locus api          # syntax check
locus init-schema                        # creates session tables incl. session_events (additive)
```
### 2. Frontend
```bash
cd web && npm install && npm run build   # tsc + vite -> dist/
```
### 3. Live stack (optional, operator-run)
```bash
docker compose up -d neo4j opensearch postgres
uvicorn api.main:app --port 8000         # EventSuggester wired with the configured LLM
cd web && npm run dev
```

## Verify Build Success
- `compileall` clean; `locus init-schema` creates `session_events` (idempotent).
- `npm run build` emits `web/dist/` with no tsc errors.
- 17 session API routes mounted (incl. events/suggest-events/approve/distortions).

## Troubleshooting
- **`session_events` missing**: run `locus init-schema` or restart app (ensure_schema is idempotent).
- **psycopg/sqlalchemy import error**: re-run `pip install -e ".[dev]"`.
- **LLM not configured**: event suggestions return `[]` (graceful); distortion/support still work.
