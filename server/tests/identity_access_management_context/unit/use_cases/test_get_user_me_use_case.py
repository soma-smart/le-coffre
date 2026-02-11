from uuid import UUID
import pytest

from identity_access_management_context.application.use_cases import (
    GetUserMeUseCase,
)
from identity_access_management_context.application.commands import GetUserMeCommand

from identity_access_management_context.domain.entities import User, SsoUser
from identity_access_management_context.domain.exceptions import UserNotFoundException
from ..fakes import FakeUserRepository, FakeSsoUserRepository


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository, sso_user_repository: FakeSsoUserRepository
):
    return GetUserMeUseCase(user_repository, sso_user_repository)


def test_given_existing_user_when_users_me_then_show_infos(
    use_case: GetUserMeUseCase, user_repository: FakeUserRepository
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
    assert result.is_sso is False


def test_given_existing_sso_user_when_users_me_then_show_infos_with_is_sso_true(
    use_case: GetUserMeUseCase,
    user_repository: FakeUserRepository,
    sso_user_repository: FakeSsoUserRepository,
):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(
        id=user_id, username="testuser", email="testuser@example.com", name="Test User"
    )
    user_repository.save(user)

    sso_user = SsoUser(
        internal_user_id=user_id,
        email="testuser@example.com",
        display_name="Test User",
        sso_user_id="sso123",
        sso_provider="google",
    )
    sso_user_repository.create(sso_user)

    command = GetUserMeCommand(requesting_user_id=user_id)

    # Act
    result = use_case.execute(command)

    # Assert
    assert result is not None
    assert result.id == user_id
    assert result.username == "testuser"
    assert result.email == "testuser@example.com"
    assert result.name == "Test User"
    assert result.is_sso is True


def test_given_not_existing_user_when_users_me_then_error(use_case: GetUserMeUseCase):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    command = GetUserMeCommand(requesting_user_id=user_id)

    # Act & Assert
    with pytest.raises(UserNotFoundException):
        use_case.execute(command)
