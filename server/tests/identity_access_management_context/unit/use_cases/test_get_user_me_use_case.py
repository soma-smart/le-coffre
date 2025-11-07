from uuid import UUID
import pytest

from identity_access_management_context.application.use_cases import (
    GetUserMeUseCase,
)
from identity_access_management_context.application.commands import GetUserMeCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import UserNotFoundException


@pytest.fixture
def use_case(user_repository: UserRepository):
    return GetUserMeUseCase(user_repository)


def test_given_existing_user_when_users_me_then_show_infos(
    use_case: GetUserMeUseCase, user_repository: UserRepository
):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    requesting_user_id = user_id
    user = User(
        id=user_id, username="testuser", email="testuser@example.com", name="Test User"
    )
    user_repository.save(user)
    command = GetUserMeCommand(user_id=user_id, requesting_user_id=requesting_user_id)

    # Act
    result = use_case.execute(command)

    # Assert
    assert result is not None
    assert result.id == user_id
    assert result.username == "testuser"
    assert result.email == "testuser@example.com"
    assert result.name == "Test User"


def test_given_not_existing_user_when_users_me_then_error(
    use_case: GetUserMeUseCase, user_repository: UserRepository
):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    requesting_user_id = user_id
    command = GetUserMeCommand(user_id=user_id, requesting_user_id=requesting_user_id)

    # Act & Assert
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_user_requests_info_for_another_user_when_users_me_then_error(
    use_case: GetUserMeUseCase, user_repository: UserRepository
):
    # Arrange
    user1_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    user2_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    user1 = User(
        id=user1_id, username="user1", email="user1@example.com", name="User One"
    )
    user2 = User(
        id=user2_id, username="user2", email="user2@example.com", name="User Two"
    )
    user_repository.save(user1)
    user_repository.save(user2)
    command = GetUserMeCommand(user_id=user2_id, requesting_user_id=user1_id)

    # Act & Assert
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)
