# =============================================================================
# Stage 1: Build Frontend
# =============================================================================
FROM oven/bun:1-alpine AS builder

WORKDIR /frontend

COPY package.json bun.lockb ./
RUN bun install --frozen-lockfile

COPY . ./
RUN bun run build

# =============================================================================
# Stage 2: Production Image (nginx)
# =============================================================================
FROM nginx:1.27-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx template (BACKEND_URL is substituted at container startup)
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Copy built frontend files
COPY --from=builder /frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
