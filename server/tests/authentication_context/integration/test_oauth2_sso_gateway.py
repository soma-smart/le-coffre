import pytest
from unittest.mock import AsyncMock, patch, Mock
from authentication_context.adapters.secondary.oauth2_sso_gateway import (
    OAuth2SsoGateway,
)
from authentication_context.domain.exceptions import InvalidSsoCodeException


@pytest.fixture
def authlib_gateway():
    gateway = OAuth2SsoGateway(
        base_url="https://oauth.example.com",
        redirect_uri="https://app.example.com/auth/callback",
        scope="openid email profile",
        provider="test",
    )
    gateway.configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint="https://oauth.example.com/authorize",
        token_endpoint="https://oauth.example.com/token",
        userinfo_endpoint="https://oauth.example.com/userinfo",
    )
    return gateway


@pytest.mark.asyncio
async def test_should_generate_authorize_url(authlib_gateway):
    # Act
    url = await authlib_gateway.get_authorize_url()

    # Assert
    assert "https://oauth.example.com/authorize" in url
    assert "client_id=test_client_id" in url
    assert "response_type=code" in url
    assert "redirect_uri=" in url


@pytest.mark.asyncio
async def test_should_validate_callback_and_return_user_info(authlib_gateway):
    # Arrange
    mock_token = {"access_token": "test_access_token", "token_type": "Bearer"}

    mock_user_info = {"sub": "123456", "email": "user@example.com", "name": "Test User"}

    with patch("httpx.AsyncClient") as mock_http_client:
        # Mock the HTTP client context manager
        mock_client_instance = AsyncMock()
        mock_http_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_http_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Mock the OAuth client
        with patch.object(authlib_gateway, "_get_oauth_client") as mock_oauth_client:
            mock_client = AsyncMock()
            mock_oauth_client.return_value = mock_client

            # Mock token exchange
            mock_client.fetch_token = AsyncMock(return_value=mock_token)

            # Mock userinfo request
            mock_response = Mock()
            mock_response.json.return_value = mock_user_info  # Synchronous
            mock_response.raise_for_status = Mock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)

            # Act
            sso_user = await authlib_gateway.validate_callback("test_code")

            # Assert
            assert sso_user.email == "user@example.com"
            assert sso_user.display_name == "Test User"
            assert sso_user.sso_user_id == "123456"
            assert sso_user.sso_provider == "test"


@pytest.mark.asyncio
async def test_should_raise_exception_for_invalid_code(authlib_gateway):
    # Arrange
    with patch("httpx.AsyncClient") as mock_http_client:
        mock_client_instance = AsyncMock()
        mock_http_client.return_value.__aenter__ = AsyncMock(
            return_value=mock_client_instance
        )
        mock_http_client.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch.object(authlib_gateway, "_get_oauth_client") as mock_oauth_client:
            mock_client = AsyncMock()
            mock_oauth_client.return_value = mock_client

            # Mock token exchange failure
            mock_client.fetch_token = AsyncMock(side_effect=Exception("Invalid code"))

            # Act & Assert
            with pytest.raises(
                InvalidSsoCodeException, match="Failed to validate SSO code"
            ):
                await authlib_gateway.validate_callback("invalid_code")


@pytest.mark.parametrize(
    "user_info,expected_email",
    [
        ({"email": "user@example.com"}, "user@example.com"),
        ({"mail": "user@example.com"}, "user@example.com"),
        ({"userPrincipalName": "user@example.com"}, "user@example.com"),
    ],
    ids=["standard_email", "microsoft_mail", "azure_ad_upn"],
)
def test_should_extract_email_from_various_formats(user_info, expected_email):
    # Arrange
    gateway = OAuth2SsoGateway(
        base_url="http://test.example.com",
        redirect_uri="http://localhost:8000/auth/sso/callback",
    )

    # Act & Assert
    assert gateway._extract_email(user_info) == expected_email


def test_should_extract_display_name_from_various_formats():
    # Arrange
    gateway = OAuth2SsoGateway(
        base_url="https://app.example.com",
        redirect_uri="https://app.example.com/auth/callback",
    )

    # Test standard name field
    user_info1 = {"name": "John Doe", "email": "john@example.com"}
    assert gateway._extract_display_name(user_info1) == "John Doe"

    # Test displayName field
    user_info2 = {"displayName": "John Doe", "email": "john@example.com"}
    assert gateway._extract_display_name(user_info2) == "John Doe"

    # Test constructed from first/last name
    user_info3 = {
        "given_name": "John",
        "family_name": "Doe",
        "email": "john@example.com",
    }
    assert gateway._extract_display_name(user_info3) == "John Doe"

    # Test fallback to email
    user_info4 = {"email": "john@example.com"}
    assert gateway._extract_display_name(user_info4) == "john@example.com"


def test_should_configure_google_with_predefined_config():
    """Test configuration with Google using hardcoded endpoints."""
    gateway = OAuth2SsoGateway(
        base_url="https://app.example.com",
        redirect_uri="https://app.example.com/auth/callback",
        provider="google",
    )

    # Configuration with Google endpoints
    gateway.configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
        token_endpoint="https://oauth2.googleapis.com/token",
        userinfo_endpoint="https://www.googleapis.com/oauth2/v2/userinfo",
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    )

    assert (
        gateway._authorization_endpoint
        == "https://accounts.google.com/o/oauth2/v2/auth"
    )
    assert gateway._token_endpoint == "https://oauth2.googleapis.com/token"
    assert gateway._userinfo_endpoint == "https://www.googleapis.com/oauth2/v2/userinfo"
    assert gateway._jwks_uri == "https://www.googleapis.com/oauth2/v3/certs"


def test_should_configure_microsoft_with_predefined_config():
    """Test configuration with Microsoft using hardcoded endpoints."""
    gateway = OAuth2SsoGateway(
        base_url="https://app.example.com",
        redirect_uri="https://app.example.com/auth/callback",
        provider="microsoft",
    )

    tenant_id = "my-tenant-123"
    # Configure Microsoft endpoints for a specific tenant
    gateway.configure(
        client_id="test_client_id",
        client_secret="test_client_secret",
        authorization_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        token_endpoint=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
        userinfo_endpoint="https://graph.microsoft.com/v1.0/me",
        jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
    )

    assert tenant_id in gateway._authorization_endpoint
    assert tenant_id in gateway._token_endpoint
    assert gateway._userinfo_endpoint == "https://graph.microsoft.com/v1.0/me"

