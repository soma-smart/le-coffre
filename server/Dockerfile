# --- Stage 1: Build ---
FROM python:3.13-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY . .

# --- Stage 2: Final Image ---
FROM python:3.13-slim

WORKDIR /app

# Créer un utilisateur non-root pour la sécurité
RUN addgroup --system app && adduser --system --group app

# Copier les dépendances installées et le code depuis le stage builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app .

# Définir le chemin pour les exécutables Python
ENV PATH=/root/.local/bin:$PATH

# Changer le propriétaire des fichiers
RUN chown -R app:app /app

# Utiliser l'utilisateur non-root
USER app

# Lancer l'application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
