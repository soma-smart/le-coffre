# Development Container Setup

This project uses a unified devcontainer that includes both frontend (Bun) and backend (Python/UV) development environments, with nginx as a reverse proxy.

## Getting Started

1. Open this project in VS Code
2. When prompted, click "Reopen in Container" or run the command "Dev Containers: Reopen in Container"
3. VS Code will automatically:
   - Detect your host user's UID and GID
   - Create a `.env` file with these values
   - Build the container with matching user permissions
   - Set up the development environment

This ensures all files created in the container have the correct ownership on your host system.

## Running the Services

Once inside the devcontainer, use VS Code Tasks:

Press `Ctrl+Shift+P` → "Run Task" → "Start All Services"

This will start nginx, backend, and frontend in separate terminal panels.

### Running Services Individually

**Nginx (Reverse Proxy)** - Start this first
Use task: "Start Nginx"

**Backend (FastAPI)**
Use task: "Start Backend" or:
```bash
cd /app/server
uv run fastapi dev src/main.py --host 0.0.0.0
```

**Frontend (Vite + Vue)**
Use task: "Start Frontend" or:
```bash
cd /app/frontend
bun dev --host 0.0.0.0
```

## Ports

- **8123**: Main development URL (nginx reverse proxy) - **Use this for development**
- **8000**: Backend API (direct access for debugging)
- **5173**: Frontend dev server (direct access for debugging)

## Why Nginx?

The frontend makes API calls to `/api/*` which need to be proxied to the backend on port 8000. Nginx handles this routing:
- Requests to `/api/*` → Backend (localhost:8000)
- All other requests → Frontend (localhost:5173)
- WebSocket support for Vite HMR

## Extensions

The devcontainer automatically installs:
- Python development tools (Pylance, Ruff, debugpy)
- Vue.js tools (Volar)
- ESLint for JavaScript/TypeScript
- SQLite viewer
- TODO tree

## Environment

- Python 3.13 with UV package manager
- Bun for frontend development
- Nginx for reverse proxy
- Git and other common development tools
