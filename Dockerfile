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

WORKDIR /backend

# Force uv to create a local virtualenv
ENV UV_PROJECT_ENVIRONMENT=/backend/.venv

COPY server/pyproject.toml server/uv.lock ./
RUN uv sync --frozen --no-dev --no-cache

COPY server/ ./


# =============================================================================
# Stage 3: Production Image
# =============================================================================
FROM python:3.13-slim

# Install runtime deps
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN addgroup --system app && adduser --system --group app

# Copy backend + venv
COPY --from=backend-builder --chown=app:app /backend /app/backend

# Copy frontend build
COPY --from=frontend-builder --chown=app:app /frontend/dist /app/frontend/dist

# -----------------------------------------------------------------------------
# NGINX config
# -----------------------------------------------------------------------------
COPY <<'EOF' /etc/nginx/sites-available/default
server {
    listen 8080;
    server_name _;

    location / {
        root /app/frontend/dist;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# -----------------------------------------------------------------------------
# Supervisor config
# -----------------------------------------------------------------------------
COPY <<'EOF' /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autorestart=true

[program:backend]
directory=/app/backend
command=/app/backend/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
user=app
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autorestart=true
EOF

# Permissions
RUN chown -R app:app /app && chmod -R 755 /app

EXPOSE 8080

# Healthcheck container-level
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
