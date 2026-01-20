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
def configured_sso(e2e_client, oidc_server):
    """
    Configure SSO with the OIDC server for the test client.
    This fixture should be used as a dependency for any test that needs SSO.
    It configures SSO once per test function.
    """
    configure_response = e2e_client.post(
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
def e2e_test_user(oidc_server):
    """
    Create a test user in the OIDC provider mock for e2e tests.
    """
    return create_sso_user_in_provider(
        oidc_server, "e2euser@example.com", "E2E Test User"
    )


@pytest.fixture
def sso_user_token(e2e_client, configured_sso, e2e_test_user):
    """
    Create and authenticate a SSO user, returning their JWT token and user info.
    This fixture handles the complete SSO flow:
    1. Configure SSO with OIDC provider (via configured_sso fixture)
    2. Get authorization URL
    3. Simulate user authorization
    4. Exchange code for token
    5. Create user in database (needed for sharing/rights features)
    """
    return authenticate_sso_user(e2e_client, configured_sso, e2e_test_user)


@pytest.fixture
def sso_user_factory(client_factory, configured_sso):
    """
    Factory fixture to create and authenticate multiple SSO users easily.
    Each user is authenticated in their own client, so this doesn't interfere
    with other authenticated clients (like authenticated_admin_client).

    Usage in tests:
        def test_example(sso_user_factory):
            user1 = sso_user_factory("alice@example.com", "Alice Smith")
            user2 = sso_user_factory("bob@example.com", "Bob Johnson")

            # user1 and user2 are dicts with: token, user_id, email, display_name
            # They also include an 'client' key with their authenticated TestClient
    """

    def _create_sso_user(email: str, name: str):
        """Create a user in OIDC provider and authenticate them with a dedicated client."""
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
    Helper function to create a user in the OIDC provider mock.

    Args:
        oidc_server: The OIDC server fixture
        email: Email address for the user (will also be used as 'sub')
        name: Full name for the user

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
    Helper function to authenticate an SSO user and get their token.
    Assumes SSO is already configured (use configured_sso fixture).

    Args:
        e2e_client: The test client
        oidc_server: The OIDC server fixture
        sso_user: User data dict with 'sub', 'email', 'name' keys

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


@pytest.fixture
def second_sso_user(oidc_server):
    """
    Create a second test user in the OIDC provider mock for multi-user tests.
    """
    return create_sso_user_in_provider(
        oidc_server, "seconduser@example.com", "Second Test User"
    )


@pytest.fixture
def second_sso_user_token(e2e_client, oidc_server, second_sso_user):
    """
    Create and authenticate a second SSO user, returning their JWT token and user info.
    """
    return authenticate_sso_user(e2e_client, oidc_server, second_sso_user)


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
    # First register an admin user
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "System Administrator",
    }

    e2e_client.post("/api/auth/register-admin", json=admin_data)

    # Then login to get the token from cookies
    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin",
        },
    )

    # Extract token from cookie
    cookies = login_response.cookies
    return cookies.get("access_token")


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
    """
    Returns a fresh TestClient without authentication.
    Uses client_factory to ensure it shares the same database and env_vars
    as other clients in the test.
    """
    return client_factory()


@pytest.fixture
def authenticated_admin_client(e2e_client):
    """
    Returns a TestClient with an authenticated admin session via cookies.
    This fixture creates an admin, logs in, and the cookies are automatically
    handled by the TestClient for subsequent requests.
    """
    # First register an admin user
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "System Administrator",
    }

    e2e_client.post("/api/auth/register-admin", json=admin_data)

    # Then login - this will set the cookies on the client
    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin",
        },
    )

    # Verify login was successful
    assert login_response.status_code == 200

    # The TestClient automatically stores cookies, so subsequent requests
    # will include the access_token cookie
    return e2e_client


@pytest.fixture
def admin_cookies(e2e_client):
    """
    Returns a dict of cookies after admin login.
    Useful for manual cookie management in tests.
    """
    # First register an admin user
    admin_data = {
        "email": "admin@example.com",
        "password": "admin",
        "display_name": "System Administrator",
    }

    e2e_client.post("/api/auth/register-admin", json=admin_data)

    # Then login to get the cookies
    login_response = e2e_client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin",
        },
    )

    # Extract cookies from response
    return login_response.cookies


@pytest.fixture
def authenticated_sso_user_client(e2e_client, oidc_server, e2e_test_user):
    """
    Returns a TestClient with an authenticated SSO user session via cookies.
    The cookies are automatically handled by the TestClient for subsequent requests.
    """
    # Configure SSO with the mock OIDC provider
    configure_response = e2e_client.post(
        "/api/auth/sso/configure",
        json={
            "client_id": oidc_server["client_id"],
            "client_secret": oidc_server["client_secret"],
            "discovery_url": oidc_server["discovery_url"],
        },
    )
    assert configure_response.status_code == 200

    # Get SSO authorization URL
    url_response = e2e_client.get("/api/auth/sso/url")
    assert url_response.status_code == 200

    sso_url_data = url_response.json()
    if isinstance(sso_url_data, str):
        sso_url = sso_url_data
    elif isinstance(sso_url_data, dict) and "url" in sso_url_data:
        sso_url = sso_url_data["url"]
    else:
        sso_url = str(sso_url_data)

    # Simulate user authorization
    auth_response = httpx.post(
        sso_url,
        data={"sub": e2e_test_user["sub"]},
        follow_redirects=False,
    )
    assert auth_response.status_code in [302, 303]

    callback_url = auth_response.headers.get("location")
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    valid_code = query_params.get("code", [None])[0]
    assert valid_code

    # Exchange code for token - this will set cookies on the client
    callback_response = e2e_client.get(f"/api/auth/sso/callback?code={valid_code}")
    assert callback_response.status_code == 200

    # The TestClient now has the cookies set
    return e2e_client


@pytest.fixture
def admin_personal_group_id(authenticated_admin_client):
    """
    Returns the personal group ID of the authenticated admin user.
    """
    response = authenticated_admin_client.get("/api/users/me")
    assert response.status_code == 200
    return response.json()["personal_group_id"]


@pytest.fixture
def sso_user_personal_group_id(authenticated_sso_user_client):
    """
    Returns the personal group ID of the authenticated SSO user.
    """
    response = authenticated_sso_user_client.get("/api/users/me")
    assert response.status_code == 200
    return response.json()["personal_group_id"]
