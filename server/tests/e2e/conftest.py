import pytest
import tempfile
import os
import httpx
import secrets
from urllib.parse import quote, urlparse, parse_qs
from fastapi.testclient import TestClient
import oidc_provider_mock

from main import app


@pytest.fixture(scope="function")
def env_vars():
    os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["JWT_ALGORITHM"] = "HS256"
    yield
    del os.environ["JWT_SECRET_KEY"]
    del os.environ["JWT_ALGORITHM"]


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
def e2e_client(database, env_vars):
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def oidc_server():
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
def configured_sso(authenticated_admin_client, oidc_server, setup):
    configure_response = authenticated_admin_client.post(
        "/api/auth/sso/configure",
        json={
            "client_id": oidc_server["client_id"],
            "client_secret": oidc_server["client_secret"],
            "discovery_url": oidc_server["discovery_url"],
        },
    )
    assert configure_response.status_code == 200, (
        f"SSO configuration failed: {configure_response.text}"
    )
    return oidc_server


@pytest.fixture
def oidc_test_user(oidc_server):
    return create_sso_user_in_provider(
        oidc_server, "e2euser@example.com", "E2E Test User"
    )


@pytest.fixture
def sso_user_token(e2e_client, configured_sso, oidc_test_user):
    return authenticate_sso_user(e2e_client, configured_sso, oidc_test_user)


@pytest.fixture
def sso_user_factory(client_factory, configured_sso):
    """
    user = sso_user_factory("alice@example.com", "Alice Smith")

    # user1 and user2 are dicts with: token, user_id, email, display_name
    """

    def _create_sso_user(email: str, name: str):
        # Create a fresh client for this user (doesn't interfere with other clients)
        user_client = client_factory()

        sso_user = create_sso_user_in_provider(configured_sso, email, name)
        user_data = authenticate_sso_user(user_client, configured_sso, sso_user)

        # Add the client to the returned data for convenience
        user_data["client"] = user_client

        return user_data

    return _create_sso_user


def create_sso_user_in_provider(oidc_server, email, name):
    """
    Returns:
        Dictionary with user data including sub, email, and name
    """
    user_data = {
        "sub": email,
        "email": email,
        "name": name,
        "given_name": name.split()[0] if " " in name else name,
        "family_name": name.split()[-1] if " " in name else "",
    }

    # Register the user with the OIDC provider
    response = httpx.put(
        f"{oidc_server['issuer_url']}/users/{quote(user_data['sub'])}",
        json=user_data,
    )
    assert response.status_code == 204, (
        f"Failed to create user {email} in OIDC provider: {response.text}"
    )

    return {
        "sub": user_data["sub"],
        "email": user_data["email"],
        "name": user_data["name"],
        "oidc_server": oidc_server,
    }


def authenticate_sso_user(e2e_client, oidc_server, sso_user):
    """
    Returns:
        Dictionary with token, user_id, email, and display_name
    """
    # Get SSO authorization URL
    url_response = e2e_client.get("/api/auth/sso/url")
    assert url_response.status_code == 200, (
        f"Failed to get SSO URL (is SSO configured?): {url_response.text}"
    )

    sso_url_data = url_response.json()
    if isinstance(sso_url_data, str):
        sso_url = sso_url_data
    elif isinstance(sso_url_data, dict) and "url" in sso_url_data:
        sso_url = sso_url_data["url"]
    else:
        sso_url = str(sso_url_data)

    # Simulate user authorization to get valid code
    auth_response = httpx.post(
        sso_url,
        data={"sub": sso_user["sub"]},
        follow_redirects=False,
    )
    assert auth_response.status_code in [
        302,
        303,
    ], f"Expected redirect, got {auth_response.status_code}"

    callback_url = auth_response.headers.get("location")
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    valid_code = query_params.get("code", [None])[0]
    assert valid_code, f"Authorization code not found in callback URL: {callback_url}"

    # Exchange code for token
    valid_callback_response = e2e_client.get(
        f"/api/auth/sso/callback?code={valid_code}"
    )
    assert valid_callback_response.status_code == 200, (
        f"Valid callback failed: {valid_callback_response.text}"
    )

    callback_data = valid_callback_response.json()
    assert "message" in callback_data, "Response should contain message"
    assert "user" in callback_data, "Response should contain user info"

    # Extract token from cookie
    token = valid_callback_response.cookies.get("access_token")
    assert token is not None, "access_token cookie should be set"

    return {
        "token": token,
        "user_id": callback_data["user"]["user_id"],
        "email": callback_data["user"]["email"],
        "display_name": callback_data["user"]["display_name"],
    }


def register_and_login_admin(client):
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "System Administrator",
    }

    client.post("/api/auth/register-admin", json=admin_data)

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin",
        },
    )
    assert login_response.status_code == 200
    return login_response


@pytest.fixture
def setup(authenticated_admin_client):
    response = authenticated_admin_client.post(
        "/api/vault/setup",
        json={
            "nb_shares": 5,
            "threshold": 3,
        },
    )
    setup_data = response.json()
    setup_id = setup_data["setup_id"]

    # Validate the setup to complete it
    authenticated_admin_client.post(
        "/api/vault/validate-setup",
        json={"setup_id": setup_id},
    )


@pytest.fixture
def admin_token(e2e_client):
    """Returns the admin JWT token extracted from cookies."""
    login_response = register_and_login_admin(e2e_client)
    return login_response.cookies.get("access_token")


@pytest.fixture
def client_factory(database, env_vars):
    """
    Factory to create TestClient instances that share the same database and env_vars.
    All clients created by this factory will use the same DATABASE_URL and JWT settings.
    """

    def _make_client():
        return TestClient(app)

    return _make_client


@pytest.fixture
def unauthenticated_client(client_factory):
    return client_factory()


@pytest.fixture
def authenticated_admin_client(e2e_client):
    register_and_login_admin(e2e_client)
    return e2e_client


@pytest.fixture
def admin_cookies(e2e_client):
    """
    Returns a dict of cookies after admin login.
    """
    login_response = register_and_login_admin(e2e_client)
    return login_response.cookies


@pytest.fixture
def authenticated_sso_user_client(e2e_client, configured_sso, oidc_test_user):
    authenticate_sso_user(e2e_client, configured_sso, oidc_test_user)
    return e2e_client


def get_personal_group_id(client):
    """
    Helper function to get the personal group ID of the authenticated user.
    """
    response = client.get("/api/users/me")
    assert response.status_code == 200
    return response.json()["personal_group_id"]


@pytest.fixture
def admin_personal_group_id(authenticated_admin_client):
    """
    Returns the personal group ID of the authenticated admin user.
    """
    return get_personal_group_id(authenticated_admin_client)


@pytest.fixture
def sso_user_personal_group_id(authenticated_sso_user_client):
    """
    Returns the personal group ID of the authenticated SSO user.
    """
    return get_personal_group_id(authenticated_sso_user_client)
