import pytest
import tempfile
import os
import httpx
from urllib.parse import quote
from fastapi.testclient import TestClient
import oidc_provider_mock

from main import app, lifespan


@pytest.fixture(scope="function")
def database():
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)  # Close the file descriptor, we just need the path

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    yield
    try:
        os.unlink(db_path)
    except OSError:
        pass
    del os.environ["DATABASE_URL"]


@pytest.fixture
def e2e_client(database):
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def oidc_server():
    """
    Start an OIDC provider mock server for e2e testing.
    """
    with oidc_provider_mock.run_server_in_thread() as server:
        issuer_url = f"http://localhost:{server.server_port}"
        yield {
            "issuer_url": issuer_url,
            "discovery_url": f"{issuer_url}/.well-known/openid-configuration",
            "server_port": server.server_port,
            "server": server,
            "client_id": "test-client",
            "client_secret": "test-secret",
            "redirect_uri": "http://localhost:8000/api/auth/sso/callback",
        }


@pytest.fixture
def e2e_test_user(oidc_server):
    """
    Create a test user in the OIDC provider mock for e2e tests.
    """
    user_data = {
        "sub": "e2euser@example.com",
        "email": "e2euser@example.com",
        "name": "E2E Test User",
        "given_name": "E2E",
        "family_name": "User",
    }
    
    # Register the user with the OIDC provider
    response = httpx.put(
        f"{oidc_server['issuer_url']}/users/{quote(user_data['sub'])}",
        json=user_data,
    )
    assert response.status_code == 204, f"Failed to create e2e test user: {response.text}"
    
    return {
        "sub": user_data["sub"],
        "email": user_data["email"],
        "name": user_data["name"],
        "oidc_server": oidc_server,
    }


@pytest.fixture
def setup(e2e_client, admin_token):
    response = e2e_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    setup_data = response.json()
    setup_id = setup_data["setup_id"]
    
    # Validate the setup to complete it
    e2e_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )


@pytest.fixture
def admin_token(e2e_client):
    # First register an admin user
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "System Administrator",
    }

    e2e_client.post("/api/auth/register-admin", json=admin_data)

    # Then login to get the token
    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin",
        },
    )
    return login_response.json()["jwt_token"]
