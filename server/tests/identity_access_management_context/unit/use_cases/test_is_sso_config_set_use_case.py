import pytest

from identity_access_management_context.application.use_cases import (
    IsSsoConfigSetUseCase,
)
from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
)
from identity_access_management_context.domain.entities import SsoConfiguration
from datetime import datetime, timezone


@pytest.fixture
def use_case(
    sso_configuration_repository: SsoConfigurationRepository,
) -> IsSsoConfigSetUseCase:
    return IsSsoConfigSetUseCase(sso_configuration_repository)


def test_given_sso_configured_when_checking_if_it_is_configured_then_should_return_true(
    use_case: IsSsoConfigSetUseCase,
    sso_configuration_repository: SsoConfigurationRepository,
):
    # Arrange
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

    # Act
    response = use_case.execute()

    # Assert
    assert response.is_set is True


def test_given_sso_not_configured_when_checking_if_it_is_configured_then_should_return_false(
    use_case: IsSsoConfigSetUseCase,
):
    # Act
    response = use_case.execute()

    # Assert
    assert response.is_set is False
