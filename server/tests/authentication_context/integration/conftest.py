import pytest
import tempfile
import os
import httpx
from urllib.parse import quote
from fastapi.testclient import TestClient
from main import app
from authentication_context.adapters.secondary import InMemorySSOGateway
import oidc_provider_mock


@pytest.fixture(scope="function")
def database():
    """Create a temporary database for testing"""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)  # Close the file descriptor, we just need the path

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    yield
    try:
        os.unlink(db_path)
    except OSError:
        pass
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]


@pytest.fixture
def api_client(database):
    """Test client for API testing"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sso_test_data():
    """Test data for SSO integration tests"""
    return {
        "valid_code_123": {
            "sso_user_id": "azure_123456789",
            "email": "john.doe@example.com",
            "display_name": "John Doe",
            "provider": "azure",
        },
        "consistent_code_456": {
            "sso_user_id": "azure_987654321",
            "email": "jane.smith@company.com",
            "display_name": "Jane Smith",
            "provider": "azure",
        },
    }


@pytest.fixture
def sso_gateway(sso_test_data):
    gateway = InMemorySSOGateway(
        authorize_url="https://test-sso.example.com/authorize",
        valid_codes=sso_test_data,
    )
    return gateway


@pytest.fixture(scope="function")
def oidc_server():
    """
    Start an OIDC provider mock server for testing.

    real OIDC endpoints for integration testing.
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
            "redirect_uri": "http://localhost:8000/auth/sso/callback",
        }


@pytest.fixture
def oidc_test_user(oidc_server):
    """
    Create a test user in the OIDC provider mock.
    
    Returns user credentials that can be used for authentication.
    """
    user_data = {
        "sub": "testuser@example.com",
        "email": "testuser@example.com",
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
    }
    
    # Register the user with the OIDC provider
    response = httpx.put(
        f"{oidc_server['issuer_url']}/users/{quote(user_data['sub'])}",
        json=user_data,
    )
    assert response.status_code == 204, f"Failed to create test user: {response.text}"
    
    return {
        "sub": user_data["sub"],
        "email": user_data["email"],
        "name": user_data["name"],
        "oidc_server": oidc_server,
    }
