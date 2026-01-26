from uuid import UUID
import pytest

from identity_access_management_context.application.use_cases import (
    GetUserMeUseCase,
)
from identity_access_management_context.application.commands import GetUserMeCommand

from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import UserNotFoundException
from ..fakes import FakeGroupRepository


@pytest.fixture
def use_case(user_repository: FakeGroupRepository):
    return GetUserMeUseCase(user_repository)


def test_given_existing_user_when_users_me_then_show_infos(
    use_case: GetUserMeUseCase, user_repository: FakeGroupRepository
):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(
        id=user_id, username="testuser", email="testuser@example.com", name="Test User"
    )
    user_repository.save(user)
    command = GetUserMeCommand(requesting_user_id=user_id)

    # Act
    result = use_case.execute(command)

    # Assert
    assert result is not None
    assert result.id == user_id
    assert result.username == "testuser"
    assert result.email == "testuser@example.com"
    assert result.name == "Test User"


def test_given_not_existing_user_when_users_me_then_error(use_case: GetUserMeUseCase):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    command = GetUserMeCommand(requesting_user_id=user_id)

    # Act & Assert
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)
