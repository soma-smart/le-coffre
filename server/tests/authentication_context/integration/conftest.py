import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from main import app
from authentication_context.adapters.secondary import InMemorySSOGateway


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


@pytest.fixture(scope="session")
def keycloak_config():
    """
    Configuration for the persistent Keycloak instance.

    This uses the Keycloak that's already running as part of docker-compose,
    configured by the setup-keycloak.sh script during devcontainer creation.
    """
    # Try to load from environment file created by setup script
    config_file = "/tmp/keycloak-test-config.env"
    config = {}

    if os.path.exists(config_file):
        with open(config_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    config[key] = value

    # Use environment variables as fallback or override
    keycloak_url = os.getenv(
        "KEYCLOAK_URL", config.get("KEYCLOAK_URL", "http://keycloak:8080")
    )
    realm_name = os.getenv("KEYCLOAK_REALM", config.get("KEYCLOAK_REALM", "master"))
    client_id = os.getenv(
        "KEYCLOAK_CLIENT_ID", config.get("KEYCLOAK_CLIENT_ID", "lecoffre-test-client")
    )
    client_secret = os.getenv(
        "KEYCLOAK_CLIENT_SECRET", config.get("KEYCLOAK_CLIENT_SECRET")
    )
    test_username = os.getenv(
        "KEYCLOAK_TEST_USERNAME", config.get("KEYCLOAK_TEST_USERNAME", "testuser")
    )
    test_password = os.getenv(
        "KEYCLOAK_TEST_PASSWORD", config.get("KEYCLOAK_TEST_PASSWORD", "testpass123")
    )
    test_email = os.getenv(
        "KEYCLOAK_TEST_EMAIL", config.get("KEYCLOAK_TEST_EMAIL", "testuser@example.com")
    )

    if not client_secret:
        pytest.skip(
            "Keycloak client secret not available. Run setup-keycloak.sh first."
        )

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "discovery_url": f"{keycloak_url}/realms/{realm_name}/.well-known/openid-configuration",
        "keycloak_url": keycloak_url,
        "realm": realm_name,
        "username": test_username,
        "password": test_password,
        "email": test_email,
        "redirect_uri": "http://localhost:8000/auth/sso/callback",
    }
