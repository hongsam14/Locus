FROM python:3.11-slim

WORKDIR /app

# System deps for healthcheck tooling (curl already in slim? ensure present)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install the package (locus = core boundaries, api = FastAPI composition root)
COPY pyproject.toml README.md ./
COPY locus ./locus
COPY api ./api
RUN pip install --no-cache-dir .

EXPOSE 8000

# docker-compose overrides this with `init-schema && uvicorn api.main:app`;
# standalone, the image only bootstraps the schemas.
CMD ["python", "-m", "locus", "init-schema"]
