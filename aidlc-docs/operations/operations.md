# Operations — Locus (placeholder)

AI-DLC Operations is a **placeholder** stage. For the MVP, operation is local via Docker Compose; no production deploy/monitoring workflow is in scope yet.

## Run (local)
```bash
./scripts/setup-volumes.sh     # create ./data bind-mount dirs (first run)
cp env.example .env            # set OPENAI_API_KEY, NEO4J_*, OPENSEARCH_*

docker compose up -d                            # infra only: neo4j + opensearch (bind-mounted ./data)
docker compose --profile tools up -d            # + OpenSearch Dashboards (:5601)
docker compose --profile service up -d --build  # + app (uvicorn :8000, runs init-schema then serves) + web (:3000)
```
- Profiles: default=infra, `service`=app+web, `tools`=dashboard. `app` needs `OPENAI_API_KEY`.
- Host dev (no app container): `docker compose up -d` then `uvicorn api.main:app --port 8000` + `cd web && npm run dev`.

## Typical workflow
1. `locus init-schema` (idempotent).
2. `locus build-wiki` (real-world priors; bundled or `--inputs`).
3. `locus build-world --world <id> --demo|--inputs <file>`.
4. Query: `GET /api/query/regions/{id}/knowledge?world_id=<id>` ; author: `/api/authoring/*`.
5. `locus export --world <id> --out <file.json>` for NPC-runtime static bundles.

## Web UI (U10)
```bash
cd web && npm install
npm run dev          # dev server :5173, proxies /api -> :8000 (run uvicorn separately)
npm run build        # static build -> web/dist (serve behind any static host / reverse proxy)
```
- Review/edit/augment UI: map-overlay topology, region knowledge, in-UI augmentation Q&A.

## Observability (current)
- Structured stdout from CLI/app; container healthchecks (Neo4j HTTP, OpenSearch cluster health).
- Dashboards/alerting: out of scope (future Operations expansion).

## Future Operations (not implemented)
- Containerized app service running uvicorn by default; CI/CD; cloud deploy; monitoring/alerting; backup of Neo4j/OpenSearch volumes; consensus cache + scaling.
