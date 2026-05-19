# =============================================================================
# Stage 1: Build Frontend
# =============================================================================
FROM oven/bun:1-alpine AS builder

WORKDIR /frontend

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . ./
RUN bun run build

# =============================================================================
# Stage 2: Production Image (nginx)
# =============================================================================
FROM nginxinc/nginx-unprivileged:alpine

USER root

# Apply latest security patches from Alpine repos
RUN apk upgrade --no-cache

USER nginx

# Copy custom nginx config and security headers snippet
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security_headers.conf /etc/nginx/security_headers.conf

# Copy built frontend files
COPY --from=builder /frontend/dist /usr/share/nginx/html

EXPOSE 8080
