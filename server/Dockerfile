# --- Stage 1: Build ---
FROM python:3.13-slim as builder

WORKDIR /app

# Install uv for dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files from server directory
COPY server/pyproject.toml server/uv.lock ./

# Install dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Copy server code
COPY server/ .

# --- Stage 2: Final Image ---
FROM python:3.13-slim

WORKDIR /app

# Créer un utilisateur non-root pour la sécurité
RUN addgroup --system app && adduser --system --group app

# Copier les dépendances installées et le code depuis le stage builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app .

# Définir le chemin pour les exécutables Python
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Changer le propriétaire des fichiers
RUN chown -R app:app /app

# Utiliser l'utilisateur non-root
USER app

# Lancer l'application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
