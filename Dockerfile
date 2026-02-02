# =============================================================================
# Stage 1: Build Frontend
# =============================================================================
FROM oven/bun:1-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package.json frontend/bun.lockb ./

# Install dependencies
RUN bun install --frozen-lockfile

# Copy frontend source
COPY frontend/ ./

# Build frontend for production
RUN bun run build

# =============================================================================
# Stage 2: Build Backend
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS backend-builder

# Update packages to patch vulnerabilities
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

WORKDIR /backend

# Copy backend dependency files
COPY server/pyproject.toml server/uv.lock ./

# Install dependencies in virtual environment
RUN uv sync --frozen --no-dev --no-cache

# Copy backend source
COPY server/ ./

# =============================================================================
# Stage 3: Production Image
# =============================================================================
FROM python:3.13-slim

# Update all packages to latest versions to patch CVEs
# This fixes CVE-2025-15467 (OpenSSL), CVE-2025-13836 (Python), and others
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user
RUN addgroup --system app && adduser --system --group app

# Copy backend from builder (including .venv)
COPY --from=backend-builder --chown=app:app /backend /app/backend

# Copy frontend build from builder
COPY --from=frontend-builder --chown=app:app /frontend/dist /app/frontend/dist

# Configure PATH to use the virtual environment
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/backend/.venv"

# Configure nginx
COPY <<'EOF' /etc/nginx/sites-available/default
server {
    listen 8080;
    server_name _;

    # Frontend static files
    location / {
        root /app/frontend/dist;
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "public, max-age=31536000, immutable";
    }

    # Backend API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

# Configure supervisor to run as non-root without HTTP server
COPY <<'EOF' /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0

[unix_http_server]
file=/tmp/supervisor.sock

[supervisorctl]
serverurl=unix:///tmp/supervisor.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autorestart=true
user=app

[program:backend]
command=/app/backend/.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000
directory=/app/backend
user=app
environment=PATH="/app/backend/.venv/bin:%(ENV_PATH)s"
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
autorestart=true
EOF

# Set permissions
RUN chown -R app:app /app && \
    chmod -R 755 /app && \
    chown -R app:app /var/log/nginx /var/lib/nginx /run && \
    chmod -R 755 /var/log/nginx /var/lib/nginx

# Switch to non-root user
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
