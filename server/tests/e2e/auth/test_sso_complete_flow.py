"""End-to-end tests for SSO routes with oidc-provider-mock.

These tests validate the FastAPI routes and request/response handling for SSO authentication.
They use oidc-provider-mock which provides real OIDC endpoints for realistic E2E testing.

Note: The app in main.py uses InMemorySSOGateway by default, which simulates SSO behavior.
For full integration with real OIDC, the app would need to be configured with OAuth2SsoGateway.
"""

import pytest
import httpx
from urllib.parse import urlparse, parse_qs


@pytest.mark.asyncio
class TestSsoRoutesE2E:
    """E2E tests for SSO routes."""

    async def test_configure_sso_provider_success(self, e2e_client, setup, oidc_server):
        """Test SSO configuration endpoint works correctly with OIDC discovery URL."""

        print("\n📝 Testing SSO configuration endpoint...")

        # Configure SSO with the mock OIDC provider's discovery URL
        response = e2e_client.post(
            "/api/auth/sso/configure",
            json={
                "client_id": oidc_server["client_id"],
                "client_secret": oidc_server["client_secret"],
                "discovery_url": oidc_server["discovery_url"],
            },
        )

        assert response.status_code == 200, f"Configuration failed: {response.text}"
        print("✅ SSO configured successfully")

    async def test_get_sso_url_after_configuration(self, e2e_client, setup, oidc_server):
        """Test getting SSO URL after configuration."""

        print("\n🔗 Testing get SSO URL endpoint...")

        # Configure first
        e2e_client.post(
            "/api/auth/sso/configure",
            json={
                "client_id": oidc_server["client_id"],
                "client_secret": oidc_server["client_secret"],
                "discovery_url": oidc_server["discovery_url"],
            },
        )

        # Get SSO URL
        url_response = e2e_client.get("/api/auth/sso/url")

        assert (
            url_response.status_code == 200
        ), f"Failed to get SSO URL: {url_response.text}"

        sso_url_data = url_response.json()

        # Handle both string response and object response
        if isinstance(sso_url_data, str):
            sso_url = sso_url_data
        elif isinstance(sso_url_data, dict) and "url" in sso_url_data:
            sso_url = sso_url_data["url"]
        else:
            sso_url = str(sso_url_data)

        assert isinstance(sso_url, str), "SSO URL should be a string"
        assert "http" in sso_url.lower(), "SSO URL should be a valid URL"
        print(f"✅ Got SSO URL: {sso_url}")

    async def test_sso_callback_with_invalid_code(self, e2e_client, setup, oidc_server):
        """Test SSO callback with invalid authorization code."""

        print("\n🧪 Testing SSO callback with invalid code...")

        # Configure SSO first
        e2e_client.post(
            "/api/auth/sso/configure",
            json={
                "client_id": oidc_server["client_id"],
                "client_secret": oidc_server["client_secret"],
                "discovery_url": oidc_server["discovery_url"],
            },
        )

        # Try callback with invalid code
        print("   🔹 Sending invalid authorization code...")
        response = e2e_client.get("/api/auth/sso/callback?code=invalid-code-12345")

        assert (
            response.status_code == 400
        ), f"Expected 400 but got {response.status_code}"
        response_data = response.json()
        assert (
            "SSO authentication failed" in response_data["detail"]
            or "invalid" in response_data["detail"].lower()
            or "fail" in response_data["detail"].lower()
        )
        print("✅ Correctly rejected invalid authorization code")

    async def test_sso_configuration_with_invalid_data(self, e2e_client, setup):
        """Test SSO configuration with invalid/missing data."""

        print("\n🧪 Testing SSO configuration validation...")

        # Test with missing client_id
        response = e2e_client.post(
            "/api/auth/sso/configure",
            json={
                "client_id": "",
                "client_secret": "test-secret",
                "discovery_url": "https://accounts.google.com/.well-known/openid-configuration",
            },
        )

        assert (
            response.status_code == 400
        ), f"Expected 400 but got {response.status_code}"
        print("✅ Correctly rejected empty client_id")

        # Test with missing fields
        response = e2e_client.post(
            "/api/auth/sso/configure",
            json={
                "client_id": "test-id",
            },
        )

        assert (
            response.status_code == 422
        ), f"Expected 422 validation error but got {response.status_code}"
        print("✅ Correctly rejected missing required fields")
