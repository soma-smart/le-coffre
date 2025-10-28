import pytest
from authentication_context.adapters.secondary.oauth2_sso_gateway import (
    OAuth2SsoGateway,
)


@pytest.fixture
def gateway():
    """Gateway configured for tests."""
    gateway = OAuth2SsoGateway(
        base_url="https://app.example.com",
        redirect_uri="https://app.example.com/auth/callback",
        provider="google",
    )
    gateway._configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint="https://example.com/auth",
        token_endpoint="https://example.com/token",
        userinfo_endpoint="https://example.com/userinfo",
    )
    return gateway


def test_configure_with_google_endpoints(gateway):
    """Test configuration with Google endpoints."""
    # Configuration with Google endpoints
    gateway._configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        userinfo_endpoint="https://www.googleapis.com/oauth2/v2/userinfo",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    )

    # Verify that endpoints are set correctly
    assert (
        gateway._authorization_endpoint
        == "https://accounts.google.com/o/oauth2/v2/auth"
    )
    assert gateway._token_endpoint == "https://oauth2.googleapis.com/token"
    assert gateway._userinfo_endpoint == "https://www.googleapis.com/oauth2/v2/userinfo"


def test_configure_with_microsoft_endpoints(gateway):
    """Test configuration with Microsoft endpoints."""
    # Configuration with Microsoft endpoints for specific tenant
    tenant_id = "my-tenant"
    gateway._configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        token_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        userinfo_endpoint="https://graph.microsoft.com/v1.0/me",
        jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
    )

    # Verify that endpoints are set correctly with the right tenant
    assert "my-tenant" in gateway._authorization_endpoint
    assert gateway._userinfo_endpoint == "https://graph.microsoft.com/v1.0/me"


def test_configure_with_custom_provider(gateway):
    """Test configuration with a custom provider."""
    gateway._configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint="https://custom.example.com/oauth/authorize",
        token_endpoint="https://custom.example.com/oauth/token",
        userinfo_endpoint="https://custom.example.com/oauth/userinfo",
    )

    assert (
        gateway._authorization_endpoint == "https://custom.example.com/oauth/authorize"
    )
    assert gateway._token_endpoint == "https://custom.example.com/oauth/token"
    assert gateway._userinfo_endpoint == "https://custom.example.com/oauth/userinfo"


@pytest.mark.asyncio
async def test_validate_callback_missing_endpoints():
    """Test validation fails if endpoints are not configured."""
    # Create gateway without configuring endpoints
    gateway = OAuth2SsoGateway(
        base_url="https://app.example.com",
        redirect_uri="https://app.example.com/auth/callback",
        provider="google",
    )
    gateway._configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint="",  # Empty endpoint
        token_endpoint="",  # Empty endpoint
        userinfo_endpoint="",  # Empty endpoint
    )

    with pytest.raises(ValueError, match="Token and userinfo endpoints not configured"):
        await gateway.validate_callback("test_code")
