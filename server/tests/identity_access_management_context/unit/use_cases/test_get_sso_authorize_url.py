import pytest
from identity_access_management_context.application.use_cases import (
    GetSsoAuthorizeUrlUseCase,
)
from identity_access_management_context.domain.entities import SsoConfiguration


@pytest.fixture
def use_case(sso_gateway, sso_configuration_repository, encryption_service):
    return GetSsoAuthorizeUrlUseCase(
        sso_gateway, sso_configuration_repository, encryption_service
    )


@pytest.mark.asyncio
async def test_should_return_sso_authorize_url(
    use_case, sso_gateway, sso_configuration_repository
):
    # Arrange
    expected_url = "https://sso.example.com/authorize"
    sso_gateway.set_authorize_url(expected_url)

    sso_configuration_repository.save(
        SsoConfiguration(
            "client_id",
            "encrypted(client_secret)",
            "url",
            "auth",
            "token",
            "userinfo",
            None,
        )
    )

    # Act
    result = await use_case.execute()

    # Assert
    assert result == expected_url


@pytest.mark.asyncio
async def test_should_raise_exception_when_no_sso_config(
    use_case: GetSsoAuthorizeUrlUseCase,
):
    # Act & Assert
    with pytest.raises(ValueError):
        await use_case.execute()
