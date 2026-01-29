# ===================================
# Stage 1: Build Frontend
# ===================================
FROM oven/bun:1-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json frontend/bun.lockb ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Build frontend for production
RUN bun run build

# ===================================
# Stage 2: Build Backend Dependencies
# ===================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend-builder

WORKDIR /app/server

# Copy backend dependency files
COPY server/pyproject.toml server/uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-cache --no-dev

# ===================================
# Stage 3: Final Production Image
# ===================================
FROM python:3.13-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Copy backend dependencies from builder
COPY --from=backend-builder /app/server/.venv /app/server/.venv

# Copy backend source code
COPY server/ /app/server/

# Copy built frontend from frontend-builder
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Set ownership
RUN chown -R app:app /app

# Set Python path
ENV PATH="/app/server/.venv/bin:$PATH" \
    PYTHONPATH="/app/server/src:$PYTHONPATH" \
    PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

USER app

# Start uvicorn directly (serves both API and frontend static files)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
