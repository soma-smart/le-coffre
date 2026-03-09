"""Tests for ConfigureSsoProviderUseCase."""

from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    ConfigureSsoProviderCommand,
)
from identity_access_management_context.application.use_cases.sso.configure_sso_provider_use_case import (
    ConfigureSsoProviderUseCase,
)
from identity_access_management_context.domain.events import SsoConfiguredEvent
from identity_access_management_context.domain.exceptions import (
    InvalidSsoSettingsException,
)
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher

from ..fakes import (
    FakeSsoConfigurationRepository,
    FakeSsoEncryptionGateway,
    FakeSsoGateway,
)


@pytest.fixture
def admin_user():
    return AuthenticatedUser(user_id=UUID("12345678-1234-5678-1234-567812345678"), roles=["admin"])


@pytest.fixture
def use_case(
    sso_gateway: FakeSsoGateway,
    sso_configuration_repository: FakeSsoConfigurationRepository,
    sso_encryption_gateway: FakeSsoEncryptionGateway,
    event_publisher,
    sso_event_repository,
):
    """Use case configured for tests."""
    return ConfigureSsoProviderUseCase(
        sso_gateway, sso_configuration_repository, sso_encryption_gateway, event_publisher, sso_event_repository
    )


@pytest.mark.asyncio
async def test_given_not_admin_when_configuring_sso_should_fail(use_case):
    """Test configuration failure for non-admin users."""
    non_admin_user = AuthenticatedUser(user_id=UUID("87654321-4321-8765-4321-876543218765"), roles=["user"])

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
    use_case, sso_configuration_repository: FakeSsoConfigurationRepository, admin_user
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
    assert config.discovery_url == "https://provider.com/.well-known/openid_configuration"
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
async def test_execute_missing_required_parameters(use_case, client_id, client_secret, discovery_url, admin_user):
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
async def test_execute_discovery_failure(use_case, sso_gateway: FakeSsoGateway, admin_user):
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


@pytest.mark.asyncio
async def test_execute_success_should_publish_sso_configured_event(
    use_case,
    admin_user,
    event_publisher: FakeDomainEventPublisher,
):
    command = ConfigureSsoProviderCommand(
        requesting_user=admin_user,
        client_id="test_client_id",
        client_secret="test_client_secret",
        discovery_url="https://provider.com/.well-known/openid_configuration",
    )
    await use_case.execute(command)

    events = event_publisher.get_published_events_of_type(SsoConfiguredEvent)
    assert len(events) == 1
    assert events[0].configured_by_user_id == admin_user.user_id
    assert events[0].discovery_url == "https://provider.com/.well-known/openid_configuration"


@pytest.mark.asyncio
async def test_execute_success_should_store_sso_configured_event(
    use_case,
    admin_user,
    sso_event_repository,
):
    command = ConfigureSsoProviderCommand(
        requesting_user=admin_user,
        client_id="test_client_id",
        client_secret="test_client_secret",
        discovery_url="https://provider.com/.well-known/openid_configuration",
    )
    await use_case.execute(command)

    assert len(sso_event_repository.events) == 1
    stored = sso_event_repository.events[0]
    assert stored["event_type"] == "SsoConfiguredEvent"
    assert stored["actor_user_id"] == admin_user.user_id
