from datetime import datetime
import pytest
import httpx
from urllib.parse import urlparse, parse_qs, quote

from identity_access_management_context.adapters.secondary import OAuth2SsoGateway
from identity_access_management_context.application.gateways import SsoGateway
from identity_access_management_context.domain.entities import SsoConfiguration


@pytest.fixture
def sso_gateway(oidc_server) -> OAuth2SsoGateway:
    """OAuth2 SSO Gateway configured to use the OIDC mock server."""
    gateway = OAuth2SsoGateway(
        redirect_uri=oidc_server["redirect_uri"],
    )
    return gateway


@pytest.mark.asyncio
async def test_configure_sso_with_oidc_discovery(sso_gateway: SsoGateway, oidc_server):
    """Test that the OIDC discovery endpoint is accessible and returns valid configuration."""

    sso_discovery_result = await sso_gateway.validate_discovery(
        client_id=oidc_server["client_id"],
        client_secret=oidc_server["client_secret"],
        discovery_url=oidc_server["discovery_url"],
    )

    config = SsoConfiguration(
        client_id=oidc_server["client_id"],
        client_secret=f"encrypted({oidc_server['client_secret']})",
        discovery_url=oidc_server["discovery_url"],
        authorization_endpoint=sso_discovery_result.authorization_endpoint,
        token_endpoint=sso_discovery_result.token_endpoint,
        userinfo_endpoint=sso_discovery_result.userinfo_endpoint,
        jwks_uri=sso_discovery_result.jwks_uri,
        updated_at=datetime.fromtimestamp(0),
        client_secret_decrypted=oidc_server["client_secret"],
    )

    auth_url = await sso_gateway.get_authorize_url(config)

    assert auth_url


@pytest.mark.asyncio
async def test_complete_oauth2_flow(sso_gateway: SsoGateway, oidc_test_user):
    """Test complete OAuth2 flow: configure -> authorize -> callback -> token exchange."""

    oidc_server = oidc_test_user["oidc_server"]

    # Step 1: Configure SSO via OIDC discovery
    sso_discovery_result = await sso_gateway.validate_discovery(
        client_id=oidc_server["client_id"],
        client_secret=oidc_server["client_secret"],
        discovery_url=oidc_server["discovery_url"],
    )

    config = SsoConfiguration(
        client_id=oidc_server["client_id"],
        client_secret=f"encrypted({oidc_server['client_secret']})",
        discovery_url=oidc_server["discovery_url"],
        authorization_endpoint=sso_discovery_result.authorization_endpoint,
        token_endpoint=sso_discovery_result.token_endpoint,
        userinfo_endpoint=sso_discovery_result.userinfo_endpoint,
        jwks_uri=sso_discovery_result.jwks_uri,
        updated_at=datetime.fromtimestamp(0),
        client_secret_decrypted=oidc_server["client_secret"],
    )

    # Step 2: Get authorization URL
    auth_url = await sso_gateway.get_authorize_url(config)
    assert auth_url, "Authorization URL should be generated"

    # Step 3: Simulate user authorization by posting directly to the mock provider
    # This simulates what happens when a user fills out the login form
    response = httpx.post(
        auth_url,
        data={"sub": oidc_test_user["sub"]},
        follow_redirects=False,
    )

    # The mock provider should redirect with an authorization code
    assert response.status_code in [
        302,
        303,
    ], f"Expected redirect, got {response.status_code}"
    callback_url = response.headers.get("location")
    assert callback_url, "Should have a redirect location"

    # Step 4: Parse authorization code from callback URL
    parsed = urlparse(callback_url)
    query_params = parse_qs(parsed.query)
    auth_code = query_params.get("code", [None])[0]

    assert auth_code, f"Authorization code not found in callback URL: {callback_url}"

    # Step 5: Exchange authorization code for tokens and user info
    sso_user = await sso_gateway.validate_callback(config, auth_code)

    # Verify SSO user data
    assert sso_user.email == oidc_test_user["email"], (
        f"Email mismatch: expected {oidc_test_user['email']}, got {sso_user.email}"
    )
    assert sso_user.display_name is not None, "Display name should be set"
    assert sso_user.sso_user_id is not None, "SSO user ID should be set"
    assert sso_user.sso_provider is not None, "SSO provider should be set"


@pytest.mark.asyncio
async def test_oauth2_flow_with_invalid_code(sso_gateway: SsoGateway, oidc_server):
    """Test that invalid authorization code is rejected."""
    sso_discovery_result = await sso_gateway.validate_discovery(
        client_id=oidc_server["client_id"],
        client_secret=oidc_server["client_secret"],
        discovery_url=oidc_server["discovery_url"],
    )

    config = SsoConfiguration(
        client_id=oidc_server["client_id"],
        client_secret=f"encrypted({oidc_server['client_secret']})",
        discovery_url=oidc_server["discovery_url"],
        authorization_endpoint=sso_discovery_result.authorization_endpoint,
        token_endpoint=sso_discovery_result.token_endpoint,
        userinfo_endpoint=sso_discovery_result.userinfo_endpoint,
        jwks_uri=sso_discovery_result.jwks_uri,
        updated_at=datetime.fromtimestamp(0),
        client_secret_decrypted=oidc_server["client_secret"],
    )
    with pytest.raises(Exception) as exc_info:
        await sso_gateway.validate_callback(config, "invalid-code-xyz123")

    # The exception should indicate authentication failure
    error_message = str(exc_info.value).lower()
    assert (
        "invalid" in error_message
        or "fail" in error_message
        or "error" in error_message
    )


@pytest.mark.asyncio
async def test_oidc_discovery_with_invalid_url(sso_gateway: SsoGateway):
    """Test that invalid discovery URL fails gracefully."""
    with pytest.raises(Exception) as exc_info:
        await sso_gateway.validate_discovery(
            client_id="test-client",
            client_secret="test-secret",
            discovery_url="https://invalid-domain-xyz123.com/.well-known/openid-configuration",
        )


@pytest.mark.asyncio
async def test_multiple_users_authentication(oidc_server, sso_gateway):
    """Test that multiple users can authenticate independently."""

    # Create two different users
    user1_data = {
        "sub": "alice@example.com",
        "email": "alice@example.com",
        "name": "Alice Smith",
    }
    user2_data = {
        "sub": "bob@example.com",
        "email": "bob@example.com",
        "name": "Bob Jones",
    }

    httpx.put(
        f"{oidc_server['issuer_url']}/users/{quote(user1_data['sub'])}",
        json=user1_data,
    )
    httpx.put(
        f"{oidc_server['issuer_url']}/users/{quote(user2_data['sub'])}",
        json=user2_data,
    )

    sso_discovery_result = await sso_gateway.validate_discovery(
        client_id=oidc_server["client_id"],
        client_secret=oidc_server["client_secret"],
        discovery_url=oidc_server["discovery_url"],
    )

    config = SsoConfiguration(
        client_id=oidc_server["client_id"],
        client_secret=f"encrypted({oidc_server['client_secret']})",
        discovery_url=oidc_server["discovery_url"],
        authorization_endpoint=sso_discovery_result.authorization_endpoint,
        token_endpoint=sso_discovery_result.token_endpoint,
        userinfo_endpoint=sso_discovery_result.userinfo_endpoint,
        jwks_uri=sso_discovery_result.jwks_uri,
        updated_at=datetime.fromtimestamp(0),
        client_secret_decrypted=oidc_server["client_secret"],
    )

    # Authenticate as user1
    auth_url1 = await sso_gateway.get_authorize_url(config)
    response1 = httpx.post(
        auth_url1, data={"sub": user1_data["sub"]}, follow_redirects=False
    )
    callback_url1 = response1.headers.get("location")
    code1 = parse_qs(urlparse(callback_url1).query).get("code", [None])[0]
    sso_user1 = await sso_gateway.validate_callback(config, code1)

    assert sso_user1.email == user1_data["email"]
    assert sso_user1.display_name == user1_data["name"]

    # Authenticate as user2
    auth_url2 = await sso_gateway.get_authorize_url(config)
    response2 = httpx.post(
        auth_url2, data={"sub": user2_data["sub"]}, follow_redirects=False
    )
    callback_url2 = response2.headers.get("location")
    code2 = parse_qs(urlparse(callback_url2).query).get("code", [None])[0]
    sso_user2 = await sso_gateway.validate_callback(config, code2)

    assert sso_user2.email == user2_data["email"]
    assert sso_user2.display_name == user2_data["name"]

    # Verify they're different users
    assert sso_user1.email != sso_user2.email
