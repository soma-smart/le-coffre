import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import (
    IsSsoConfigSetUseCase,
)
from identity_access_management_context.application.commands import (
    IsSsoConfigSetCommand,
)
from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
)
from identity_access_management_context.domain.entities import SsoConfiguration
from shared_kernel.authentication import AuthenticatedUser, NotAdminError
from datetime import datetime, timezone


@pytest.fixture
def use_case(
    sso_configuration_repository: SsoConfigurationRepository,
) -> IsSsoConfigSetUseCase:
    return IsSsoConfigSetUseCase(sso_configuration_repository)


def test_given_admin_user_when_sso_is_configured_then_should_return_true(
    use_case: IsSsoConfigSetUseCase,
    sso_configuration_repository: SsoConfigurationRepository,
):
    # Arrange
    admin_user = AuthenticatedUser(
        user_id=UUID("123e4567-e89b-12d3-a456-426614174000"), roles=["admin"]
    )
    sso_config = SsoConfiguration(
        client_id="test-client-id",
        client_secret="encrypted-secret",
        discovery_url="https://example.com/.well-known/openid_configuration",
        authorization_endpoint="https://example.com/authorize",
        token_endpoint="https://example.com/token",
        userinfo_endpoint="https://example.com/userinfo",
        jwks_uri="https://example.com/jwks",
        updated_at=datetime.now(timezone.utc),
    )
    sso_configuration_repository.save(sso_config)
    command = IsSsoConfigSetCommand(requesting_user=admin_user)

    # Act
    response = use_case.execute(command)

    # Assert
    assert response.is_set is True


def test_given_admin_user_when_sso_is_not_configured_then_should_return_false(
    use_case: IsSsoConfigSetUseCase,
    sso_configuration_repository: SsoConfigurationRepository,
):
    # Arrange
    admin_user = AuthenticatedUser(
        user_id=UUID("123e4567-e89b-12d3-a456-426614174000"), roles=["admin"]
    )
    command = IsSsoConfigSetCommand(requesting_user=admin_user)

    # Act
    response = use_case.execute(command)

    # Assert
    assert response.is_set is False


def test_given_non_admin_user_when_checking_sso_config_then_should_raise_not_admin_error(
    use_case: IsSsoConfigSetUseCase,
):
    # Arrange
    regular_user = AuthenticatedUser(
        user_id=UUID("123e4567-e89b-12d3-a456-426614174000"), roles=[]
    )
    command = IsSsoConfigSetCommand(requesting_user=regular_user)

    # Act & Assert
    with pytest.raises(NotAdminError):
        use_case.execute(command)
