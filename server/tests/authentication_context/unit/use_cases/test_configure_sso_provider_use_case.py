"""Tests for ConfigureSsoProviderUseCase."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from authentication_context.application.use_cases.sso.configure_sso_provider_use_case import (
    ConfigureSsoProviderUseCase,
)
from authentication_context.domain.exceptions import InvalidSsoSettingsException


@pytest.fixture
def mock_sso_gateway():
    """Mock SSO Gateway."""
    gateway = MagicMock()
    gateway.configure_with_discovery = AsyncMock()
    return gateway


@pytest.fixture
def use_case(mock_sso_gateway):
    """Use case configured for tests."""
    return ConfigureSsoProviderUseCase(mock_sso_gateway)


@pytest.mark.asyncio
async def test_execute_success_with_auto_discovery(use_case, mock_sso_gateway):
    """Test successful configuration with auto-discovery."""
    await use_case.execute(
        client_id="test_client_id",
        client_secret="test_client_secret",
        discovery_url="https://provider.com/.well-known/openid_configuration",
    )

    # Verify that configure_with_discovery was called with correct parameters
    mock_sso_gateway.configure_with_discovery.assert_called_once_with(
        client_id="test_client_id",
        client_secret="test_client_secret",
        discovery_url="https://provider.com/.well-known/openid_configuration",
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client_id, client_secret, discovery_url",
    [
        ("", "test_secret", "https://provider.com/.well-known/openid_configuration"),
        ("test_client_id", "", "https://provider.com/.well-known/openid_configuration"),
        ("test_client_id", "test_secret", ""),
    ],
)
async def test_execute_missing_required_parameters(
    use_case, client_id, client_secret, discovery_url
):
    """Test validation with missing required parameters."""
    with pytest.raises(
        InvalidSsoSettingsException,
        match="Client ID, client secret, and discovery URL are required",
    ):
        await use_case.execute(
            client_id=client_id,
            client_secret=client_secret,
            discovery_url=discovery_url,
        )


@pytest.mark.asyncio
async def test_execute_discovery_failure(use_case, mock_sso_gateway):
    """Test configuration failure due to discovery error."""
    # Configure mock to raise ValueError (simulating discovery failure)
    mock_sso_gateway.configure_with_discovery.side_effect = ValueError("HTTP 404")

    with pytest.raises(InvalidSsoSettingsException, match="Auto-discovery failed"):
        await use_case.execute(
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://invalid-provider.com/.well-known/openid_configuration",
        )


@pytest.mark.asyncio
async def test_execute_missing_required_discovery_fields(use_case, mock_sso_gateway):
    """Test discovery with missing required fields."""
    # Configure mock to raise ValueError (simulating missing fields)
    mock_sso_gateway.configure_with_discovery.side_effect = ValueError(
        "Missing fields in discovery: ['token_endpoint']"
    )

    with pytest.raises(InvalidSsoSettingsException, match="Auto-discovery failed"):
        await use_case.execute(
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://provider.com/.well-known/openid_configuration",
        )


@pytest.mark.asyncio
async def test_execute_gateway_configuration_failure(use_case, mock_sso_gateway):
    """Test configuration failure due to gateway error."""
    # Configure mock to raise a generic Exception (simulating gateway failure)
    mock_sso_gateway.configure_with_discovery.side_effect = Exception("Gateway error")

    with pytest.raises(InvalidSsoSettingsException, match="Configuration failed"):
        await use_case.execute(
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://provider.com/.well-known/openid_configuration",
        )
