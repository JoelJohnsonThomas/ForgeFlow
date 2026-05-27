# ================================================================
# ForgeFlow Multi-Stage Dockerfile
# Targets: base → api | mcp | dashboard
#
# Hardening (SECURITY_AUDIT.md §8):
#   - Wheels are built in a `builder` stage that carries gcc + libpq-dev.
#   - The runtime stages copy only the installed Python packages — no
#     compilers ship to production.
#   - All runtime stages drop to a non-root `app` user (UID 1000).
# ================================================================

# --- builder: compiles wheels for asyncpg/psycopg ---
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# --- runtime base: slim Python, no compilers ---
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Runtime needs libpq for psycopg/asyncpg shared objects, but not the -dev
# headers or a compiler. curl stays for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home /app --shell /sbin/nologin app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels


# ================================================================
# api — FastAPI application server
# ================================================================
FROM base AS api

COPY forgeflow/ ./forgeflow/
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "forgeflow.api.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ================================================================
# mcp — FastMCP tool server
# ================================================================
FROM base AS mcp

COPY forgeflow/ ./forgeflow/

RUN chown -R app:app /app
USER app

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "forgeflow.mcp.server.main", "http"]


# ================================================================
# dashboard — Streamlit observability dashboard
# ================================================================
FROM base AS dashboard

COPY dashboard/ ./dashboard/
COPY forgeflow/config.py ./forgeflow/config.py
COPY forgeflow/__init__.py ./forgeflow/__init__.py

RUN chown -R app:app /app
USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
