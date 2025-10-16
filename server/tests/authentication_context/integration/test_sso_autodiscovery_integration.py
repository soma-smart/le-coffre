"""Integration tests for SSO auto-discovery."""

import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_configure_sso_with_autodiscovery(api_client):
    """Test configuration SSO with OpenID Connect auto-discovery."""

    # Patch the function in the use case now
    with patch(
        "authentication_context.application.use_cases.configure_sso_provider_use_case.ConfigureSsoProviderUseCase._discover_endpoints"
    ) as mock_discover:
        mock_discover.return_value = {
            "authorization_endpoint": "https://test-provider.com/auth",
            "token_endpoint": "https://test-provider.com/token",
            "userinfo_endpoint": "https://test-provider.com/userinfo",
            "jwks_uri": "https://test-provider.com/certs",
        }

        # Test with auto-discovery
        response = api_client.post(
            "/auth/sso/configure",
            json={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "discovery_url": "https://test-provider.com/.well-known/openid_configuration",
            },
        )

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_configure_sso_with_autodiscovery_error(api_client):
    """Test SSO configuration with auto-discovery error."""
    with patch(
        "authentication_context.application.use_cases.configure_sso_provider_use_case.ConfigureSsoProviderUseCase._discover_endpoints"
    ) as mock_discover:
        mock_discover.side_effect = ValueError("Error discovering endpoints: HTTP 404")

        response = api_client.post(
            "/auth/sso/configure",
            json={
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
                "discovery_url": "https://invalid-provider.com/.well-known/openid_configuration",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Auto-discovery failed" in data["detail"]


@pytest.mark.asyncio
async def test_configure_sso_missing_discovery_url(api_client):
    """Test error when discovery_url is missing."""
    response = api_client.post(
        "/auth/sso/configure",
        json={
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            # discovery_url missing
        },
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
