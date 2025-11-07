import pytest
from uuid import UUID

from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.use_cases import (
    CreateAdminUseCase,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import AdminAlreadyExistsError


@pytest.fixture
def use_case(user_repository: UserRepository):
    return CreateAdminUseCase(user_repository)


def test_should_create_admin(
    use_case: CreateAdminUseCase,
    user_repository: UserRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"

    command = CreateUserCommand(id=uuid, username=username, email=email, name=name)

    user_id = use_case.execute(command)

    created_user = user_repository.get_by_id(user_id)
    assert created_user is not None
    assert created_user.id == uuid
    assert created_user.username == username
    assert created_user.email == email
    assert created_user.name == name
    assert "admin" in created_user.roles


def test_when_admin_exist_should_not_create_a_second_one(
    use_case: CreateAdminUseCase, user_repository: UserRepository
):
    first_admin = User(
        id=UUID("321e4567-e89b-12d3-a456-426614174000"),
        username="admin",
        email="admin@example.com",
        name="Admin User",
        roles=["admin"],
    )
    user_repository.save(first_admin)

    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"

    command = CreateUserCommand(id=uuid, username=username, email=email, name=name)

    with pytest.raises(AdminAlreadyExistsError):
        use_case.execute(command)
