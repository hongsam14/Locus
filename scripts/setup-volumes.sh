#!/bin/bash
# Initialize local bind-mount data directories for Docker volumes (Locus).
set -e

echo "Setting up Locus data directories..."

mkdir -p data/neo4j/data
mkdir -p data/neo4j/logs
mkdir -p data/neo4j/import
mkdir -p data/neo4j/plugins
mkdir -p data/opensearch

# Make the (empty) mount dirs world-writable so the container UIDs (Neo4j 7474,
# OpenSearch 1000) can write on first start. `|| true`: once a container owns its
# data, the host user can no longer chmod those files — that's expected, not fatal.
for d in data/neo4j/data data/neo4j/logs data/neo4j/import data/neo4j/plugins data/opensearch; do
  chmod 777 "$d" 2>/dev/null || true
done

echo "✓ Data directories created:"
echo "  data/"
echo "  ├── neo4j/"
echo "  │   ├── data/    (Neo4j database files)"
echo "  │   ├── logs/    (Neo4j logs)"
echo "  │   ├── import/  (APOC import dir)"
echo "  │   └── plugins/ (APOC plugin jar)"
echo "  └── opensearch/  (OpenSearch data)"
echo ""
echo "Next steps:"
echo "  1. cp env.example .env   # set OPENAI_API_KEY, NEO4J_PASSWORD, ..."
echo "  2. docker compose up -d                      # infra only (neo4j + opensearch)"
echo "     docker compose --profile tools up -d      # + OpenSearch Dashboards (:5601)"
echo "     docker compose --profile service up -d --build   # + app (:8000) + web (:3000)"
echo "  3. Neo4j Browser: http://localhost:7474"
