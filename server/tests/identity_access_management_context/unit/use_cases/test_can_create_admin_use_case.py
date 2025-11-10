import pytest

from identity_access_management_context.application.use_cases import (
    CanCreateAdminUseCase,
)
from identity_access_management_context.adapters.secondary import InMemoryUserRepository

from identity_access_management_context.domain.entities import User
from shared_kernel.domain import ADMIN_ROLE
from uuid import uuid4


@pytest.fixture
def user_repository():
    return InMemoryUserRepository()


@pytest.fixture
def use_case(user_repository) -> CanCreateAdminUseCase:
    return CanCreateAdminUseCase(user_repository)


def test_can_create_admin_when_no_admin_exists(use_case):
    # Act
    response = use_case.execute()

    # Assert
    assert response.can_create is True


def test_cannot_create_admin_when_admin_already_exists(use_case, user_repository):
    # Arrange

    admin = User(
        id=uuid4(),
        username="admin",
        email="admin@example.com",
        name="Admin User",
        roles=[ADMIN_ROLE],
    )
    user_repository.save(admin)

    # Act
    response = use_case.execute()

    # Assert
    assert response.can_create is False


def test_can_create_admin_when_only_regular_users_exist(use_case, user_repository):
    # Arrange
    regular_user = User(
        id=uuid4(),
        username="user",
        email="user@example.com",
        name="Regular User",
        roles=[],  # No admin role
    )
    user_repository.save(regular_user)

    # Act
    response = use_case.execute()

    # Assert
    assert response.can_create is True
