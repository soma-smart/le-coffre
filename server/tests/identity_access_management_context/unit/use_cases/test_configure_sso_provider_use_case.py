"""Tests for ConfigureSsoProviderUseCase."""

import pytest
from uuid import UUID
from shared_kernel.authentication import AuthenticatedUser
from identity_access_management_context.application.commands import (
    ConfigureSsoProviderCommand,
)
from identity_access_management_context.application.use_cases.sso.configure_sso_provider_use_case import (
    ConfigureSsoProviderUseCase,
)
from identity_access_management_context.domain.exceptions import (
    InvalidSsoSettingsException,
)
from shared_kernel.authentication.exceptions import NotAdminError


@pytest.fixture
def admin_user():
    return AuthenticatedUser(
        user_id=UUID("12345678-1234-5678-1234-567812345678"), roles=["admin"]
    )


@pytest.fixture
def use_case(sso_gateway, sso_configuration_repository, encryption_service):
    """Use case configured for tests."""
    return ConfigureSsoProviderUseCase(
        sso_gateway, sso_configuration_repository, encryption_service
    )


@pytest.mark.asyncio
async def test_given_not_admin_when_configuring_sso_should_fail(use_case):
    """Test configuration failure for non-admin users."""
    non_admin_user = AuthenticatedUser(
        user_id=UUID("87654321-4321-8765-4321-876543218765"), roles=["user"]
    )

    command = ConfigureSsoProviderCommand(
        requesting_user=non_admin_user,
        client_id="test_client_id",
        client_secret="test_client_secret",
        discovery_url="https://provider.com/.well-known/openid_configuration",
    )

    with pytest.raises(NotAdminError):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_execute_success_with_auto_discovery(
    use_case, sso_configuration_repository, admin_user
):
    """Test successful configuration with auto-discovery."""
    command = ConfigureSsoProviderCommand(
        requesting_user=admin_user,
        client_id="test_client_id",
        client_secret="test_client_secret",
        discovery_url="https://provider.com/.well-known/openid_configuration",
    )
    await use_case.execute(command)

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
    use_case, client_id, client_secret, discovery_url, admin_user
):
    """Test validation with missing required parameters."""
    with pytest.raises(
        InvalidSsoSettingsException,
        match="Client ID, client secret, and discovery URL are required",
    ):
        command = ConfigureSsoProviderCommand(
            requesting_user=admin_user,
            client_id=client_id,
            client_secret=client_secret,
            discovery_url=discovery_url,
        )
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_execute_discovery_failure(use_case, sso_gateway, admin_user):
    """Test configuration failure due to discovery error."""
    sso_gateway.set_discovery_error(ValueError("HTTP 404"))

    with pytest.raises(InvalidSsoSettingsException, match="Auto-discovery failed"):
        command = ConfigureSsoProviderCommand(
            requesting_user=admin_user,
            client_id="test_client_id",
            client_secret="test_client_secret",
            discovery_url="https://invalid-provider.com/.well-known/openid_configuration",
        )
        await use_case.execute(command)
