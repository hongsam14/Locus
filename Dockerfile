FROM python:3.11-slim

WORKDIR /app

# System deps for healthcheck tooling (curl already in slim? ensure present)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install the package
COPY pyproject.toml README.md ./
COPY locus ./locus
RUN pip install --no-cache-dir .

EXPOSE 8000

# Default command is overridden by docker-compose (U1: init-schema + idle).
CMD ["python", "-m", "locus", "init-schema"]
