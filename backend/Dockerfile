# ── Stage 1: dependency builder ───────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install uv --no-cache-dir

# Copy only dependency manifests first (layer cache)
COPY pyproject.toml uv.lock ./

# Sync production deps only into a virtual environment at /app/.venv
RUN uv sync --frozen --no-dev

# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Security: non-root user
RUN groupadd --gid 1001 eios && \
    useradd --uid 1001 --gid eios --no-create-home --shell /bin/false eios

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY --chown=eios:eios . .

# Remove test artifacts from the runtime image
RUN rm -rf tests/ eios_backend.egg-info/

# Add the venv to PATH so python / uvicorn are found without activation
ENV PATH="/app/.venv/bin:$PATH"

USER eios

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2} --no-access-log"]
