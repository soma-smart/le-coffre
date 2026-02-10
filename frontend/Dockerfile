# --- Stage 1: Build ---
FROM oven/bun:1-slim AS builder

WORKDIR /app

# Copy dependency files
COPY package.json bun.lockb ./

# Install dependencies
RUN bun install --frozen-lockfile --production=false

# Copy application source code
COPY . .

# Build the application
RUN bun run build

# --- Stage 2: Serve with lightweight HTTP server ---
FROM node:22-alpine

WORKDIR /app

# Install a simple, production-ready static file server
RUN npm install -g serve

# Create non-root user for security
RUN addgroup -g 1000 app && \
    adduser -u 1000 -G app -s /bin/sh -D app

# Copy built assets from builder stage
COPY --from=builder --chown=app:app /app/dist /app/dist

# Switch to non-root user
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

# Serve static files with SPA fallback
# The -s flag enables SPA mode (rewrites all not-found requests to /index.html)
# The -l flag sets the port
CMD ["serve", "-s", "dist", "-l", "8080"]
