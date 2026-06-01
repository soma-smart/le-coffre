# Le Coffre

<p align="center">
   <img src="frontend/public/img/le-coffre.png" alt="Le Coffre Logo" width="300">
</p>

Le Coffre is an open-source password manager that allows you to securely store and manage passwords in a collaboration-friendly environment.

> 🇫🇷 Proudly supported by [SOMA 🦊](https://www.soma-smart.com)

## Application

### Setup and Encrypt Le Coffre in seconds
![Setup Vault](media/setup.gif)

### Creation, Update, Sharing of Passwords ultra secure
![Create password](media/create_password.gif)

### Group system easy to use
![Group](media/group_view.png)

### SSO
![SSO](media/SSO.png)

### Password audit
![Audit Password](media/audit_password.png)

### Admin view
![List Users](media/admin_users_page.png)

## Simple to deploy

### Docker images
> ghcr.io/soma-smart/le-coffre-backend:tag_version (or latest)<br>
> ghcr.io/soma-smart/le-coffre-frontend:tag_version (or latest)

### Docker compose
```bash
# 1. Create your env file
cp .env.example .env

# 2. Generate a secret key
echo "JWT_SECRET_KEY=$(openssl rand -base64 32)" >> .env
```

**Option A — external database** (recommended): set `DATABASE_URL` in `.env`, then:
```bash
docker compose up -d
```

**Option B — bundled PostgreSQL**: set `POSTGRES_PASSWORD` in `.env`, then:
```bash
docker compose --profile postgres up -d
```

Visit <http://localhost> and you're done

### In local

[See here](#Development)


# Tech
## Frontend ([README.md](frontend/README.md))

- Vue 3 + Vite
- PrimeVue 4 (UI components)
- Tailwind CSS
- Pinia (state management)
- Zod (schema validation)

## Backend ([README.md](server/README.md))

- FastAPI
- SQLModel + Alembic (ORM & migrations)
- PyCryptodome (AES encryption, Shamir's Secret Sharing)
- Authlib (SSO / OAuth2 OIDC), PyJWT (auth tokens)
- passlib + bcrypt (password hashing)

# Development

## Using Devcontainer (Recommended)

Open with VSCode and reopen in the devcontainer when prompted. The unified devcontainer includes both frontend and backend development environments with nginx as a reverse proxy.

**Quick Start:**

1. Open project in VS Code
2. Click "Reopen in Container" when prompted
3. Use VS Code tasks to start services (`Ctrl+Shift+P` → "Tasks: Run Task"):
   - **Start All Services** — nginx + backend + frontend (runs inside the dev container)
   - **Run Keycloak (local SSO)** — starts a local Keycloak for testing the SSO flow and prints the credentials on every run. Works from inside the dev container (the `docker-outside-of-docker` feature gives it the Docker CLI + host socket) or from a host terminal.

See [.devcontainer/README.md](.devcontainer/README.md) for detailed instructions.

### Testing SSO locally (Keycloak)

Run the **Run Keycloak (local SSO)** VS Code task — or, from the host, `docker compose -f docker-compose.dev.yml --profile sso up -d keycloak`. It boots Keycloak with a preconfigured `lecoffre` realm (a client + a test user) and prints everything you need:

- Keycloak admin console: <http://localhost:8180> (`admin` / `admin`)
- In Le Coffre, open **Admin → SSO** (unlock the vault first) and enter:
  - **Client ID:** `lecoffre-client`
  - **Client secret:** `lecoffre-dev-secret`
  - **Discovery URL:** `http://keycloak:8080/realms/lecoffre/.well-known/openid-configuration`
- Then "Login with SSO" using the seeded user: `testuser` / `password`

> The discovery URL uses `keycloak:8080` because the **backend** reaches Keycloak over the Docker network, while the **browser** is redirected to `http://localhost:8180` to log in — Keycloak is configured to keep the issuer consistent across both. It runs in-memory (`start-dev`), so the realm re-imports on each start. The realm lives in `dev/keycloak/lecoffre-realm.json` and the `keycloak` service in `docker-compose.dev.yml` (behind the `sso` compose profile). Stop it with `docker compose -f docker-compose.dev.yml --profile sso down`.

**Access Points:**

- **Main App:** <http://127.0.0.1:8123> (via nginx - use this for development)
- Frontend (direct): <http://127.0.0.1:5173>
- Backend API (direct): <http://127.0.0.1:8000>
- API Docs: <http://127.0.0.1:8000/docs>
- OpenAPI Spec: <http://127.0.0.1:8000/openapi.json>

> **Why nginx?** The frontend makes API calls to `/api/*` which are proxied to the backend. Always use port 8123 for development.

# Security

## Implementation

See [CRYPTOGRAPHIC_ARCHITECTURE.md](CRYPTOGRAPHIC_ARCHITECTURE.md)

## Considerations

See [SECURITY.md](SECURITY.md).
