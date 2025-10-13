# --- Stage 1: Build ---
FROM oven/bun:latest AS builder-front

WORKDIR /app/frontend

COPY frontend/ ./

RUN bun install

RUN bun run build-only


# Stage 2: Build dependencies
FROM python:3.13-slim AS builder-back

WORKDIR /app/server

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copier les fichiers de configuration du projet
COPY server/pyproject.toml server/uv.lock* ./

RUN uv sync --frozen --no-cache --no-dev
RUN uv add gunicorn uvicorn


# --- Stage 3: Final Image ---
FROM python:3.13-slim

RUN apt-get update && apt-get upgrade -y

# Créer un utilisateur non-root pour la sécurité
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# Copier les dépendances installées et le code depuis le stage builder
COPY --from=builder-front /app/frontend/dist/ ./static

# Copy virtual environment from build stage
COPY --from=builder-back /app/server/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copier le code source de l'application
COPY server/src/ ./

# Changer le propriétaire des fichiers
RUN chown -R app:app /app

# Utiliser l'utilisateur non-root
USER app

# Exposer le port de l'API
EXPOSE 9081

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9081"]
