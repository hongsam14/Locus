#!/bin/bash
# Initialize local bind-mount data directories for Docker volumes (Locus).
set -e

echo "Setting up Locus data directories..."

mkdir -p data/neo4j/data
mkdir -p data/neo4j/logs
mkdir -p data/neo4j/import
mkdir -p data/neo4j/plugins
mkdir -p data/opensearch
mkdir -p data/postgres

# Make the (empty) mount dirs world-writable so the container UIDs (Neo4j 7474,
# OpenSearch 1000, Postgres 999) can write on first start. `|| true`: once a
# container owns its data, the host user can no longer chmod those files — that's
# expected, not fatal.
for d in data/neo4j/data data/neo4j/logs data/neo4j/import data/neo4j/plugins data/opensearch data/postgres; do
  chmod 777 "$d" 2>/dev/null || true
done

echo "✓ Data directories created:"
echo "  data/"
echo "  ├── neo4j/"
echo "  │   ├── data/    (Neo4j database files)"
echo "  │   ├── logs/    (Neo4j logs)"
echo "  │   ├── import/  (APOC import dir)"
echo "  │   └── plugins/ (APOC plugin jar)"
echo "  ├── opensearch/  (OpenSearch data)"
echo "  └── postgres/    (PostgreSQL session data)"
echo ""
echo "Next steps:"
echo "  1. cp env.example .env   # REQUIRED: NEO4J_PASSWORD, SESSION_DB_PASSWORD (OPENAI_API_KEY optional)"
echo "  2. docker compose --profile service up -d --build   # infra + app (:8000) + web (:3000)"
echo "     docker compose up -d                             # or infra only (neo4j + opensearch + postgres)"
echo "     docker compose --profile tools up -d dashboard   # + OpenSearch Dashboards (:5601)"
echo "  3. Open http://localhost:3000 and press [play now] on a demo card"
echo "  Stop: docker compose --profile service --profile tools down"
