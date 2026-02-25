# Le-Coffre backend

## Start the backend

- install uv
```bash
pip install uv
```

- install the dependencies
```bash
uv sync
```

- run the server
```bash
uv run fastapi dev src/main.py
```

## Optional: monitoring (OpenTelemetry)

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

## Run the tests

To have the tests run automatically on file changes, you can use the `ptw` command:
```bash
uv run ptw .
```

Or classic pytest:
```bash
uv run pytest
```

Tests that require OpenTelemetry are automatically skipped if the `monitoring` group is not installed.
