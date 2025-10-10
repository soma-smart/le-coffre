import pytest
from authentication_context.domain.exceptions import InvalidSsoCodeException


@pytest.mark.asyncio
async def test_should_return_authorize_url(sso_gateway):
    # Act
    url = await sso_gateway.get_authorize_url()

    # Assert
    assert isinstance(url, str)
    assert url.startswith("https://")
    assert url == "https://test-sso.example.com/authorize"


@pytest.mark.asyncio
async def test_should_validate_valid_sso_code_and_return_user_info(sso_gateway):
    # Arrange
    valid_code = "valid_code_123"

    # Act
    sso_user = await sso_gateway.validate_callback(valid_code)

    # Assert
    assert sso_user.internal_user_id is not None
    assert sso_user.email == "john.doe@example.com"
    assert sso_user.display_name == "John Doe"
    assert sso_user.sso_user_id == "azure_123456789"
    assert sso_user.sso_provider == "azure"


@pytest.mark.asyncio
async def test_should_raise_exception_for_invalid_sso_code(sso_gateway):
    # Arrange
    invalid_code = "invalid_code_999"

    # Act & Assert
    with pytest.raises(InvalidSsoCodeException) as exc_info:
        await sso_gateway.validate_callback(invalid_code)

    assert "Invalid SSO code" in str(exc_info.value)


@pytest.mark.asyncio
async def test_should_return_consistent_user_for_same_code(sso_gateway):
    # Arrange
    code = "consistent_code_456"

    # Act
    user1 = await sso_gateway.validate_callback(code)
    user2 = await sso_gateway.validate_callback(code)

    # Assert - Same SSO data but different internal UUIDs (as expected)
    assert user1.sso_user_id == user2.sso_user_id == "azure_987654321"
    assert user1.email == user2.email == "jane.smith@company.com"
    assert user1.display_name == user2.display_name == "Jane Smith"
    assert user1.sso_provider == user2.sso_provider == "azure"


def test_should_set_sso_settings(sso_gateway):
    # Arrange
    client_id = "new_client_id_abc"
    client_secret = "new_client_secret_xyz"

    # Act
    sso_gateway.set_settings(client_id, client_secret)

    # Assert
    assert sso_gateway._client_id == client_id
    assert sso_gateway._client_secret == client_secret
