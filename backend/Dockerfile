# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv --no-cache-dir

# Copy only dependency manifests first (layer cache)
COPY pyproject.toml uv.lock ./

# Install dependencies into a fixed prefix; exclude dev extras
RUN uv sync --frozen --no-dev --prefix /install

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --gid 1001 eios && \
    useradd --uid 1001 --gid eios --no-create-home --shell /bin/false eios

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install/lib /usr/local/lib
COPY --from=builder /install/bin /usr/local/bin

# Copy application source
COPY --chown=eios:eios . .

# Remove test artifacts and dev tooling from the image
RUN rm -rf tests/ .venv/ *.egg-info/ alembic/versions/__pycache__/

USER eios

# Expose the application port
EXPOSE 8000

# Health check — liveness endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production entry point
# --workers 2 is a conservative default for 1–2 vCPU containers
# Override with WORKERS env var: docker run -e WORKERS=4 ...
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2} --no-access-log"]
