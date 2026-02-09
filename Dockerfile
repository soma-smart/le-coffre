# =============================================================================
# Stage 1: Build Frontend
# =============================================================================
FROM oven/bun:1-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package.json frontend/bun.lockb ./
RUN bun install --frozen-lockfile

COPY frontend/ ./
RUN bun run build


# =============================================================================
# Stage 2: Build Backend
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend-builder

# Install build dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Force uv to create a local virtualenv
ENV UV_PROJECT_ENVIRONMENT=/app/backend/.venv

COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev --no-cache --group postgres

COPY server/ ./


# =============================================================================
# Stage 3: Production Image
# =============================================================================
FROM python:3.13-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN addgroup --system app && adduser --system --group app

# Copy backend + venv
COPY --from=backend-builder --chown=app:app /app/backend /app/backend

# Copy frontend build
COPY --from=frontend-builder --chown=app:app /frontend/dist /app/frontend/dist

# Switch to non-root user
USER app

# Set working directory to backend
WORKDIR /app/backend

# Set environment variables for production
ENV PYTHONPATH=/app/backend/src \
    PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Healthcheck using Python
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD ["/app/backend/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health').read()"]

# Run FastAPI with uvicorn
CMD ["/app/backend/.venv/bin/uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--log-level", "info"]
