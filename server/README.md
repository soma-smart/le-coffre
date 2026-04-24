# Le Coffre — Backend

FastAPI backend for the Le Coffre password manager.

**Stack:** FastAPI, SQLModel, Alembic, PyCryptodome, Authlib, passlib (bcrypt), PyJWT, Python 3.13+

## Start the backend

- Install [uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- Install the dependencies

```bash
uv sync
```

- Run the server

```bash
uv run fastapi dev src/main.py --host 0.0.0.0
```

## Environment variables

| Variable | Required | Description | Default |
|---|---|---|---|
| `DATABASE_URL` | No | SQLAlchemy database URL | `sqlite:///local_db.sqlite` |
| `JWT_SECRET_KEY` | **Yes (prod)** | Secret key for signing JWTs (≥ 32 chars) | Random (dev only) |
| `JWT_ALGORITHM` | No | JWT signing algorithm | `HS256` |
| `JWT_ACCESS_TOKEN_EXPIRATION_MINUTES` | No | Access token lifetime (minutes) | `5` |
| `JWT_REFRESH_TOKEN_EXPIRATION_HOURS` | No | Refresh token lifetime (hours) | `4` |
| `ENVIRONMENT` | No | Set to `production` to enable secure cookies and production settings | `development` |
| `RATE_LIMIT_ENABLED` | No | Enable/disable rate limiting | `true` |
| `RATE_LIMIT_WINDOW_SECONDS` | No | Sliding window duration (seconds) | `60` |
| `RATE_LIMIT_USER_MAX_REQUESTS` | No | Per-authenticated-user bucket | `300` |
| `RATE_LIMIT_UNAUTH_MAX_REQUESTS` | No | Per-IP bucket for unauthenticated callers | `30` |
| `RATE_LIMIT_AUTH_MAX_REQUESTS` | No | Per-IP volume floor on `/api/auth/login` only | `100` |
| `RATE_LIMIT_TRUSTED_PROXIES` | No | Comma-separated TCP peer IPs whose `X-Forwarded-For` is trusted | `127.0.0.1,::1` |
| `RATE_LIMIT_TRUSTED_PROXY_HOPS` | No | Number of trusted proxy hops between client and backend | `1` |
| `LOGIN_MAX_FAILED_ATTEMPTS` | No | Consecutive failed logins before an account is locked | `5` |
| `LOGIN_LOCKOUT_SECONDS` | No | Duration in seconds an account stays locked | `300` |

## Optional: monitoring (OpenTelemetry)

# TODO Gautier: update this when monitoring is validated

The server supports distributed tracing and metrics via OpenTelemetry. This is **opt-in** — the application runs fully without it.

To enable it locally:

```bash
uv sync --group monitoring
```

Then set the required environment variables before starting the server:

| Variable | Description |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint (e.g. `http://localhost:4318`) |
| `OTEL_SERVICE_NAME` | Service name reported to the collector (default: `le-coffre`) |
| `ENABLE_MONITORING` | Set to `true` to force-enable even without an endpoint, or `false` to hard-disable |

## Database migrations

When you add or modify a SQLModel table:

1. Make your changes to the model files in `src/*/adapters/secondary/sql/model/`
2. Create a migration:

   ```bash
   cd server
   uv run alembic revision --autogenerate -m "Add new_column to UserTable"
   ```

3. Review the generated file in `alembic/versions/`.
See [server/tests/alembic/test_migrations.py](tests/alembic/test_migrations.py) for complete migrations test.

4. Test the migration:

   ```bash
   uv run alembic upgrade head  # Apply
   uv run alembic downgrade -1  # Rollback
   uv run alembic upgrade head  # Re-apply
   ```

5. Commit the migration file to version control

See [server/alembic/README.md](alembic/README.md) for migration full documentation.

## Run the tests

```bash
uv run pytest .
```

Tests that require OpenTelemetry are automatically skipped if the `monitoring` group is not installed.

## Formatting

To ensure code quality, work in the dev container that it is automatically applied, or run these command:

```bash
uv run ruff format .
uv run ruff check .
```
