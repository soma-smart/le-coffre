# --- Stage 1: Build frontend ---
FROM oven/bun:latest AS builder-front

WORKDIR /app/frontend
COPY frontend/ ./
RUN bun install && bun run build-only


# --- Stage 2: Build dependencies backend ---
FROM python:3.13-slim AS builder-back

WORKDIR /app/server
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY server/pyproject.toml server/uv.lock* ./

RUN uv sync --frozen --no-cache --no-dev


# --- Stage 3: Final image ---
FROM python:3.13-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    addgroup --system app && \
    adduser --system --group app

WORKDIR /app

# Copy installed dependencies and code from the builder stage
COPY --from=builder-front /app/frontend/dist/ ./static

# Copy virtual environment from build stage
COPY --from=builder-back /app/server/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application source code
COPY server/src/ ./

# Change the owner of the files
RUN chown -R app:app /app

# Use non-root user
USER app

# Expose the API port
EXPOSE 8000

ENTRYPOINT ["python", "-m", "uvicorn", "main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
