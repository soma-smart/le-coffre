"""Integration tests for SSO auto-discovery."""

import pytest
from unittest.mock import patch, AsyncMock
from authentication_context.adapters.secondary.oauth2_sso_gateway import (
    OAuth2SsoGateway,
)


@pytest.mark.asyncio
async def test_configure_sso_with_autodiscovery(api_client):
    """Test configuration SSO with OpenID Connect auto-discovery."""

    with patch.object(
        OAuth2SsoGateway, "configure_with_discovery", new_callable=AsyncMock
    ) as mock_configure:
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
        mock_configure.assert_called_once_with(
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://test-provider.com/.well-known/openid_configuration",
        )


@pytest.mark.asyncio
async def test_configure_sso_with_autodiscovery_error(api_client):
    """Test SSO configuration with auto-discovery error."""
    with patch.object(
        OAuth2SsoGateway, "configure_with_discovery", new_callable=AsyncMock
    ) as mock_configure:
        mock_configure.side_effect = ValueError("Error discovering endpoints: HTTP 404")

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
