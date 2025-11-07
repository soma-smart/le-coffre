import pytest
from uuid import UUID

from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.use_cases import CreateUserUseCase
from identity_access_management_context.domain.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
)


@pytest.fixture
def use_case(user_repository: UserRepository):
    return CreateUserUseCase(user_repository)


def test_should_create_user(
    use_case: CreateUserUseCase,
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


def test_should_raise_when_user_already_exists(
    use_case: CreateUserUseCase,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"

    command = CreateUserCommand(id=uuid, username=username, email=email, name=name)

    use_case.execute(command)
    with pytest.raises(UserAlreadyExistsError) as _:
        use_case.execute(command)
