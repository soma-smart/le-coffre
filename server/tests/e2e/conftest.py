import os
import secrets
import tempfile
from urllib.parse import parse_qs, quote, urlparse

import httpx
import oidc_provider_mock
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from alembic import command
from main import app


class CsrfTestClient(TestClient):
    """
    TestClient wrapper that automatically adds CSRF token to mutating requests.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._csrf_token = None
        self._auto_csrf = True  # Flag to enable/disable auto CSRF injection

    def disable_auto_csrf(self):
        """Temporarily disable automatic CSRF token injection."""
        self._auto_csrf = False

    def enable_auto_csrf(self):
        """Re-enable automatic CSRF token injection."""
        self._auto_csrf = True

    def _get_csrf_token(self, force_refresh=False):
        """Fetch CSRF token from the API."""
        if not self._csrf_token or force_refresh:
            try:
                response = super().get("/api/auth/csrf-token")
                if response.status_code == 200:
                    self._csrf_token = response.json()["csrf_token"]
            except Exception:
                # Token not available or not authenticated yet
                pass
        return self._csrf_token

    def refresh_csrf_token(self):
        """Force refresh the CSRF token (call after login)."""
        return self._get_csrf_token(force_refresh=True)

    def post(self, *args, **kwargs):
        """POST with automatic CSRF token injection."""
        return self._request_with_csrf(super().post, *args, **kwargs)

    def put(self, *args, **kwargs):
        """PUT with automatic CSRF token injection."""
        return self._request_with_csrf(super().put, *args, **kwargs)

    def delete(self, *args, **kwargs):
        """DELETE with automatic CSRF token injection."""
        return self._request_with_csrf(super().delete, *args, **kwargs)

    def patch(self, *args, **kwargs):
        """PATCH with automatic CSRF token injection."""
        return self._request_with_csrf(super().patch, *args, **kwargs)

    def _request_with_csrf(self, method, *args, **kwargs):
        """Add CSRF token header if available and not already present."""
        # Get or create headers dict
        headers = kwargs.get("headers", {})
        if isinstance(headers, dict):
            headers = dict(headers)  # Make a copy
        else:
            # Convert to dict if it's another type
            headers = dict(headers)

        # Add CSRF token if auto-csrf is enabled and token not already present
        if self._auto_csrf and "X-CSRF-Token" not in headers and "x-csrf-token" not in headers:
            token = self._get_csrf_token()
            if token:
                headers["X-CSRF-Token"] = token

        kwargs["headers"] = headers
        return method(*args, **kwargs)


@pytest.fixture(scope="session")
def env_vars():
    os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["JWT_ALGORITHM"] = "HS256"
    # Use very high rate limits so e2e tests are not impacted
    os.environ["RATE_LIMIT_AUTH_MAX_REQUESTS"] = "1000"
    os.environ["RATE_LIMIT_API_MAX_REQUESTS"] = "1000"
    yield
    del os.environ["JWT_SECRET_KEY"]
    del os.environ["JWT_ALGORITHM"]
    os.environ.pop("RATE_LIMIT_AUTH_MAX_REQUESTS", None)
    os.environ.pop("RATE_LIMIT_API_MAX_REQUESTS", None)


@pytest.fixture(scope="session")
def database_path():
    """Create a temporary database file with schema applied once for the entire test session."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Run Alembic migrations once for the whole session
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")
    command.upgrade(alembic_cfg, "head")

    yield db_path

    try:
        os.unlink(db_path)
    except OSError:
        pass
    del os.environ["DATABASE_URL"]


@pytest.fixture(scope="function")
def database(database_path):
    """
    Function-scoped fixture that cleans the database before each test.
    Uses the session-scoped database file but deletes all rows between tests.

    This ensures complete test isolation by truncating all application tables
    while keeping the schema (avoiding expensive Alembic re-migrations).
    """
    engine = create_engine(f"sqlite:///{database_path}")

    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        conn.commit()

        result = conn.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table'"
                " AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
            )
        )
        tables = [row[0] for row in result]

        for table in tables:
            conn.execute(text(f'DELETE FROM "{table}"'))

        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.commit()

    engine.dispose()
    yield database_path


@pytest.fixture
def e2e_client(database, env_vars):
    with CsrfTestClient(app) as client:
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


@pytest.fixture(scope="session")
def sso_configuration_data(oidc_server):
    """
    Session-scoped fixture that provides SSO configuration data.
    This doesn't configure SSO in the database, just provides the config values.
    """
    return {
        "client_id": oidc_server["client_id"],
        "client_secret": oidc_server["client_secret"],
        "discovery_url": oidc_server["discovery_url"],
    }


@pytest.fixture
def configured_sso(authenticated_admin_client, oidc_server, setup, database_path):
    """
    Function-scoped fixture that configures SSO for a test.
    The configuration is cleaned up by the database fixture between tests.
    """
    configure_response = authenticated_admin_client.post(
        "/api/auth/sso/configure",
        json={
            "client_id": oidc_server["client_id"],
            "client_secret": oidc_server["client_secret"],
            "discovery_url": oidc_server["discovery_url"],
        },
    )
    assert configure_response.status_code == 200, f"SSO configuration failed: {configure_response.text}"
    return oidc_server


@pytest.fixture
def oidc_test_user(oidc_server):
    return create_sso_user_in_provider(oidc_server, "e2euser@example.com", "E2E Test User")


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
    # PUT is idempotent, so 204 means success (created or already exists)
    assert response.status_code == 204, f"Failed to create user {email} in OIDC provider: {response.text}"

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
    assert url_response.status_code == 200, f"Failed to get SSO URL (is SSO configured?): {url_response.text}"

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
    valid_callback_response = e2e_client.get(f"/api/auth/sso/callback?code={valid_code}")
    assert valid_callback_response.status_code == 200, f"Valid callback failed: {valid_callback_response.text}"

    callback_data = valid_callback_response.json()
    assert "message" in callback_data, "Response should contain message"
    assert "user" in callback_data, "Response should contain user info"

    # Extract token from cookie
    token = valid_callback_response.cookies.get("access_token")
    assert token is not None, "access_token cookie should be set"

    # Refresh CSRF token after authentication (for CsrfTestClient)
    if hasattr(e2e_client, "refresh_csrf_token"):
        e2e_client.refresh_csrf_token()

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

    # Register admin (should succeed since database is clean for each test)
    register_response = client.post("/api/auth/register-admin", json=admin_data)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@example.com",
            "password": "admin",
        },
    )
    assert login_response.status_code == 200

    # Refresh CSRF token after login (for CsrfTestClient)
    if hasattr(client, "refresh_csrf_token"):
        client.refresh_csrf_token()

    return login_response


@pytest.fixture(scope="session")
def session_vault_setup_data(database_path, env_vars):
    """
    Session-scoped vault setup that runs once.
    Returns the setup configuration (shares, threshold).
    """
    return {
        "nb_shares": 5,
        "threshold": 3,
    }


@pytest.fixture
def setup(authenticated_admin_client, session_vault_setup_data):
    """
    Function-scoped fixture that ensures vault is set up for the test.
    Performs setup only once per test (fast if already done).
    """
    # Check if vault is already setup
    status_response = authenticated_admin_client.get("/api/vault/status")

    if status_response.status_code == 200:
        status = status_response.json()
        # If vault is already setup and validated, we're done
        if status.get("is_setup") and not status.get("needs_validation"):
            return

    # Otherwise, perform setup
    response = authenticated_admin_client.post(
        "/api/vault/setup",
        json=session_vault_setup_data,
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
    Factory to create CsrfTestClient instances that share the same database and env_vars.
    All clients created by this factory will use the same DATABASE_URL and JWT settings.
    """

    def _make_client():
        return CsrfTestClient(app)

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
