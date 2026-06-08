#!/bin/bash
# Initialize local bind-mount data directories for Docker volumes (Locus).
set -e

echo "Setting up Locus data directories..."

mkdir -p data/neo4j/data
mkdir -p data/neo4j/logs
mkdir -p data/opensearch

# Permissions: Neo4j runs as UID 7474, OpenSearch as UID 1000.
chmod -R 755 data/neo4j
chmod -R 777 data/opensearch   # OpenSearch needs write access to its data dir

echo "✓ Data directories created:"
echo "  data/"
echo "  ├── neo4j/"
echo "  │   ├── data/   (Neo4j database files)"
echo "  │   └── logs/   (Neo4j logs)"
echo "  └── opensearch/ (OpenSearch data)"
echo ""
echo "Next steps:"
echo "  1. cp env.example .env   # set OPENAI_API_KEY, NEO4J_PASSWORD, ..."
echo "  2. docker compose up -d                      # infra only (neo4j + opensearch)"
echo "     docker compose --profile tools up -d      # + OpenSearch Dashboards (:5601)"
echo "     docker compose --profile service up -d --build   # + app (:8000) + web (:3000)"
echo "  3. Neo4j Browser: http://localhost:7474"
