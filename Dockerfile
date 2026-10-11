FROM python:3.11-slim

WORKDIR /app

# curl for the compose healthcheck (`curl -sf http://localhost:8000/health`)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install the locus package (pyproject installs `locus*` only, with the demo data); `api`
# (the FastAPI composition root) stays as source under /app and imports from the WORKDIR
COPY pyproject.toml README.md LICENSE ./
COPY locus ./locus
COPY api ./api
RUN pip install --no-cache-dir .

EXPOSE 8000

# docker-compose overrides this with `init-schema && uvicorn api.main:app`;
# standalone, the image only bootstraps the schemas.
CMD ["python", "-m", "locus", "init-schema"]
