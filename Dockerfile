ARG NODE_ENV=production
ARG NODE_VERSION=20-bullseye-slim

# Use a lightweight and production-optimized Node.js image
FROM node:${NODE_VERSION} AS builder

# Install only the necessary tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the application files
COPY . /app/

# Install Node.js dependencies in production mode
# Build the application
RUN npm install && \
    npm run build && \
    npm prune --production

# Production stage
FROM node:${NODE_VERSION} AS runner

# Install only the necessary tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security reasons
# Create the working directory and set permissions
RUN useradd -m lecoffreuser && \
    mkdir -p /app && \
    chown -R lecoffreuser:lecoffreuser /app
WORKDIR /app

# Switch to the non-root user
USER lecoffreuser

# Copy the built application from the builder stage
COPY --from=builder --chown=lecoffreuser:lecoffreuser /app/.output/ /app/
COPY --from=builder --chown=lecoffreuser:lecoffreuser /app/server/database/migrations /app/server/database/migrations

# Expose the port used by the application
EXPOSE 3000

# Define the entrypoint
ENTRYPOINT ["node", "/app/server/index.mjs"]
