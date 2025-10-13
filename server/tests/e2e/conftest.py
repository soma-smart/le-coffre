import pytest
import tempfile
import os
from fastapi.testclient import TestClient

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
