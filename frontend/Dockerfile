# --- Stage 1: Build ---
# Construit l'application Vue
FROM oven/bun:latest as builder

WORKDIR /app

COPY package.json bun.lockb ./
RUN bun install
COPY . .
RUN bun run build

# --- Stage 2: Final Image ---
# Sert les fichiers statiques avec Nginx
FROM nginx:stable-alpine

# Copier les fichiers statiques buildés depuis le stage précédent
COPY --from=builder /app/dist /usr/share/nginx/html

# Copier la configuration Nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Exposer le port 80
EXPOSE 80

# La commande par défaut de l'image nginx est de démarrer le serveur
CMD ["nginx", "-g", "daemon off;"]
