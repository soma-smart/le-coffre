"""Tests for ConfigureSsoProviderUseCase."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from authentication_context.application.use_cases.configure_sso_provider_use_case import (
    ConfigureSsoProviderUseCase,
)
from authentication_context.domain.exceptions import InvalidSsoSettingsException


@pytest.mark.asyncio
class TestConfigureSsoProviderUseCase:
    """Tests for ConfigureSsoProviderUseCase."""

    @pytest.fixture
    def mock_sso_gateway(self):
        """Mock SSO Gateway."""
        gateway = MagicMock()
        return gateway

    @pytest.fixture
    def use_case(self, mock_sso_gateway):
        """Use case configured for tests."""
        return ConfigureSsoProviderUseCase(mock_sso_gateway)

    async def test_execute_success_with_auto_discovery(
        self, use_case, mock_sso_gateway
    ):
        """Test successful configuration with auto-discovery."""
        mock_config = {
            "authorization_endpoint": "https://provider.com/auth",
            "token_endpoint": "https://provider.com/token",
            "userinfo_endpoint": "https://provider.com/userinfo",
            "jwks_uri": "https://provider.com/certs",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_config
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            await use_case.execute(
                client_id="test_client_id",
                client_secret="test_client_secret",
                discovery_url="https://provider.com/.well-known/openid_configuration",
            )

            # Verify the gateway was configured correctly
            mock_sso_gateway.configure.assert_called_once_with(
                client_id="test_client_id",
                client_secret="test_client_secret",
                authorization_endpoint="https://provider.com/auth",
                token_endpoint="https://provider.com/token",
                userinfo_endpoint="https://provider.com/userinfo",
                jwks_uri="https://provider.com/certs",
            )

    async def test_execute_missing_required_parameters(self, use_case):
        """Test validation with missing required parameters."""
        with pytest.raises(
            InvalidSsoSettingsException,
            match="Client ID, client secret, and discovery URL are required",
        ):
            await use_case.execute(
                client_id="",
                client_secret="test_secret",
                discovery_url="https://provider.com/.well-known/openid_configuration",
            )

        with pytest.raises(
            InvalidSsoSettingsException,
            match="Client ID, client secret, and discovery URL are required",
        ):
            await use_case.execute(
                client_id="test_id",
                client_secret="",
                discovery_url="https://provider.com/.well-known/openid_configuration",
            )

        with pytest.raises(
            InvalidSsoSettingsException,
            match="Client ID, client secret, and discovery URL are required",
        ):
            await use_case.execute(
                client_id="test_id",
                client_secret="test_secret",
                discovery_url="",
            )

    async def test_execute_discovery_failure(self, use_case, mock_sso_gateway):
        """Test configuration failure due to discovery error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("HTTP 404")

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(
                InvalidSsoSettingsException, match="Auto-discovery failed"
            ):
                await use_case.execute(
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    discovery_url="https://invalid-provider.com/.well-known/openid_configuration",
                )

            # Verify that the gateway was not called
            mock_sso_gateway.configure.assert_not_called()

    async def test_execute_missing_required_discovery_fields(
        self, use_case, mock_sso_gateway
    ):
        """Test discovery with missing required fields."""
        mock_config = {
            "authorization_endpoint": "https://provider.com/auth"
            # Missing token_endpoint
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_config
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(
                InvalidSsoSettingsException, match="Auto-discovery failed"
            ):
                await use_case.execute(
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    discovery_url="https://provider.com/.well-known/openid_configuration",
                )

            # Verify that the gateway was not called
            mock_sso_gateway.configure.assert_not_called()

    async def test_execute_gateway_configuration_failure(
        self, use_case, mock_sso_gateway
    ):
        """Test failure when gateway configuration fails."""
        mock_config = {
            "authorization_endpoint": "https://provider.com/auth",
            "token_endpoint": "https://provider.com/token",
            "userinfo_endpoint": "https://provider.com/userinfo",
            "jwks_uri": "https://provider.com/certs",
        }

        # Configure gateway to raise an exception
        mock_sso_gateway.configure.side_effect = Exception(
            "Gateway configuration failed"
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_config
            mock_response.raise_for_status = MagicMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            with pytest.raises(
                InvalidSsoSettingsException, match="Configuration failed"
            ):
                await use_case.execute(
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                    discovery_url="https://provider.com/.well-known/openid_configuration",
                )
