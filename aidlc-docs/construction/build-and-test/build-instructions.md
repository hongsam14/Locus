# Build Instructions — Locus

## Prerequisites
- **Language/Build**: Python 3.11+ (tested on 3.13), `pip` / `setuptools`.
- **Dependencies**: see `pyproject.toml` (pydantic v2, pydantic-settings, neo4j, opensearch-py, langchain, langchain-openai, langgraph, openai, tenacity, fastapi, uvicorn; dev: pytest, pytest-cov, hypothesis, black, ruff, mypy).
- **Env vars**: `.env` from `env.example` (`OPENAI_API_KEY`, `NEO4J_*`, `OPENSEARCH_*`, `EMBEDDING_*`).
- **System**: Docker + Docker Compose for Neo4j 5.x + OpenSearch 2.x (integration). Unit tests need no services.

## Build Steps

### 1. Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp env.example .env   # fill OPENAI_API_KEY etc.
```

### 2. Configure environment (integration only)
```bash
docker-compose up -d neo4j opensearch     # deps only (host dev)
# or: docker-compose up -d                # full stack (app + deps)
```

### 3. Build / install package
```bash
pip install -e .            # importable package + `locus` CLI entry
locus --help                # verify CLI (init-schema/build-wiki/build-world/export)
```

### 4. Verify build success
- **Expected**: `pip install -e .` completes; `python -c "import api.main, locus.__main__"` succeeds; `locus --help` lists 4 commands.
- **Artifacts**: `locus/` importable package, `api.main:app` (FastAPI), `locus` console script.
- **Acceptable warnings**: FastAPI `on_event` deprecation (startup hook); harmless.

## Troubleshooting
- **Dependency errors**: ensure Python 3.11+; `pip install --upgrade pip`. Heavy deps (langchain/neo4j/opensearch) are lazily imported — unit tests run with a minimal subset, but full install is needed for the app/CLI.
- **Import errors for `api`**: run from repo root (the `api/` package is at workspace root, alongside `locus/`).
