"""Tests for ConfigureSsoProviderUseCase."""

import pytest
from identity_access_management_context.application.use_cases.sso.configure_sso_provider_use_case import (
    ConfigureSsoProviderUseCase,
)
from identity_access_management_context.domain.exceptions import (
    InvalidSsoSettingsException,
)


@pytest.fixture
def use_case(sso_gateway, sso_configuration_repository, encryption_service):
    """Use case configured for tests."""
    return ConfigureSsoProviderUseCase(
        sso_gateway, sso_configuration_repository, encryption_service
    )


@pytest.mark.asyncio
async def test_execute_success_with_auto_discovery(
    use_case, sso_gateway, sso_configuration_repository
):
    """Test successful configuration with auto-discovery."""
    await use_case.execute(
        client_id="test_client_id",
        client_secret="test_client_secret",
        discovery_url="https://provider.com/.well-known/openid_configuration",
    )

    # Verify configuration was saved with encrypted client secret
    config = sso_configuration_repository.get()
    assert config is not None
    assert config.client_id == "test_client_id"
    assert config.client_secret == "encrypted(test_client_secret)"
    assert (
        config.discovery_url == "https://provider.com/.well-known/openid_configuration"
    )
    assert config.authorization_endpoint == "https://provider.com/authorize"
    assert config.token_endpoint == "https://provider.com/token"
    assert config.userinfo_endpoint == "https://provider.com/userinfo"


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
async def test_execute_discovery_failure(use_case, sso_gateway):
    """Test configuration failure due to discovery error."""
    sso_gateway.set_discovery_error(ValueError("HTTP 404"))

    with pytest.raises(InvalidSsoSettingsException, match="Auto-discovery failed"):
        await use_case.execute(
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://invalid-provider.com/.well-known/openid_configuration",
        )
