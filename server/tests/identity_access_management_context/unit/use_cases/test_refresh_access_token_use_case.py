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
from ..fakes import FakeTokenGateway, FakeUserRepository, FakeTimeGateway


@pytest.fixture
def use_case(
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
    time_provider: FakeTimeGateway,
):
    return RefreshAccessTokenUseCase(
        token_gateway=token_gateway,
        user_repository=user_repository,
        time_provider=time_provider,
    )


@pytest.mark.asyncio
async def test_given_valid_refresh_token_when_execute_then_returns_new_access_token(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
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
    token_gateway: FakeTokenGateway,
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


@pytest.mark.asyncio
async def test_given_user_promoted_to_admin_when_refresh_token_then_new_token_has_updated_roles(
    use_case: RefreshAccessTokenUseCase,
    token_gateway: FakeTokenGateway,
    user_repository: FakeUserRepository,
):
    # Arrange
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    email = "promoted@example.com"

    # User initially has only "user" role
    old_roles = ["user"]
    refresh_token = "valid_refresh_token_before_promotion"

    # Create user with initial roles
    user = User(
        id=user_id,
        username="promoted_user",
        email=email,
        name="Promoted User",
        roles=old_roles,
    )
    user_repository.save(user)

    # Refresh token was issued with old roles
    token_gateway.set_valid_refresh_token(refresh_token, user_id, email, old_roles)

    # User gets promoted to admin (roles updated in database)
    user.promote_to_admin()
    user_repository.update(user)

    # Get updated user from repository to verify promotion
    updated_user = user_repository.get_by_id(user_id)
    assert "admin" in updated_user.roles, "User should have admin role in database"

    token_gateway.set_unique_jwt_part("new_token_after_promotion")

    command = RefreshAccessTokenCommand(refresh_token=refresh_token)

    # Act
    result = await use_case.execute(command)

    # Assert
    assert result.access_token == f"jwt_token_for_{user_id}_new_token_after_promotion"

    # Verify that the new token was generated with CURRENT roles from database
    # (not with stale roles from the old refresh token)
    last_generated_token = token_gateway.get_last_generated_token()
    assert last_generated_token is not None, "Token should have been generated"
    assert "admin" in last_generated_token.roles, (
        "New access token should include admin role from database"
    )
    assert last_generated_token.roles == ["user", "admin"], (
        "New access token should have current roles: ['user', 'admin']"
    )
