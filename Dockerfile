# ================================================================
# ForgeFlow Multi-Stage Dockerfile
# Targets: base → api | mcp | dashboard
# ================================================================

# --- base: shared Python + deps ---
FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps for asyncpg + psycopg + pgvector
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ================================================================
# api — FastAPI application server
# ================================================================
FROM base AS api

COPY forgeflow/ ./forgeflow/
COPY alembic/ ./alembic/
COPY alembic.ini ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "forgeflow.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ================================================================
# mcp — FastMCP tool server
# ================================================================
FROM base AS mcp

COPY forgeflow/ ./forgeflow/

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

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "dashboard/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
