from main import app


def test_db_routes_return_503_while_migrations_in_progress(e2e_client):
    app.state.ready = False
    app.state.migration_failed = False
    try:
        response = e2e_client.get("/api/vault/status")
        assert response.status_code == 503
        assert response.json()["detail"] == "Service starting: database migrations in progress"
    finally:
        app.state.ready = True


def test_db_routes_return_503_when_migrations_failed(e2e_client):
    app.state.ready = False
    app.state.migration_failed = True
    try:
        response = e2e_client.get("/api/vault/status")
        assert response.status_code == 503
        assert response.json()["detail"] == "Service unavailable: database migrations failed"
    finally:
        app.state.ready = True
        app.state.migration_failed = False


def test_health_probes_stay_reachable_while_not_ready(e2e_client):
    app.state.ready = False
    app.state.migration_failed = False
    try:
        liveness = e2e_client.get("/api/health")
        assert liveness.status_code == 200

        readiness = e2e_client.get("/api/health/ready")
        assert readiness.status_code == 503  # honestly reports "not ready"
    finally:
        app.state.ready = True


def test_db_routes_served_normally_once_ready(e2e_client):
    app.state.ready = True
    response = e2e_client.get("/api/vault/status")
    assert response.status_code == 200
