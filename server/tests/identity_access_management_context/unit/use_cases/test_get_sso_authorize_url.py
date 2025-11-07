import pytest
from identity_access_management_context.application.use_cases.sso.get_sso_authorize_url_use_case import (
    GetSsoAuthorizeUrlUseCase,
)


@pytest.fixture
def use_case(sso_gateway):
    return GetSsoAuthorizeUrlUseCase(sso_gateway)


@pytest.mark.asyncio
async def test_should_return_sso_authorize_url(use_case, sso_gateway):
    # Arrange
    expected_url = "https://sso.example.com/authorize"
    sso_gateway.set_authorize_url(expected_url)

    # Act
    result = await use_case.execute()

    # Assert
    assert result == expected_url
