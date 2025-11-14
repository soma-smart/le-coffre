import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import (
    RefreshAccessTokenUseCase,
)
from identity_access_management_context.application.commands import (
    RefreshAccessTokenCommand,
)
from identity_access_management_context.domain.exceptions import (
    InvalidRefreshTokenException,
)
from identity_access_management_context.domain.entities import User


@pytest.fixture
def use_case(token_gateway, user_repository):
    return RefreshAccessTokenUseCase(
        token_gateway=token_gateway,
        user_repository=user_repository,
    )


@pytest.mark.asyncio
async def test_given_valid_refresh_token_when_execute_then_returns_new_access_token(
    use_case: RefreshAccessTokenUseCase,
    token_gateway,
    user_repository,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "user@example.com"
    roles = ["user"]
    refresh_token = "valid_refresh_token_123"

    user = User(
        id=user_id, username="testuser", email=email, name="Test User", roles=roles
    )
    user_repository.save(user)

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles)
    token_gateway.set_unique_jwt_part("new_access_token")

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result.access_token == f"jwt_token_for_{user_id}_new_access_token"
    assert result.user_id == user_id


@pytest.mark.asyncio
async def test_given_invalid_refresh_token_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
):
    # Arrange
    invalid_refresh_token = "invalid_token_xyz"
    command = RefreshAccessTokenCommand(refresh_token=invalid_refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_given_expired_refresh_token_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
):
    # Arrange
    expired_refresh_token = "expired_token_abc"
    command = RefreshAccessTokenCommand(refresh_token=expired_refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_given_refresh_token_for_nonexistent_user_when_execute_then_raises_invalid_refresh_token_exception(
    use_case: RefreshAccessTokenUseCase,
    token_gateway,
    user_repository,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "deleted@example.com"
    roles = ["user"]
    refresh_token = "valid_token_for_deleted_user"

    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, roles)
    # User does not exist in repository (not added)

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act & Assert
    with pytest.raises(InvalidRefreshTokenException):
        await use_case.execute(command)
