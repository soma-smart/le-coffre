import pytest
from uuid import UUID

from user_management_context.application.interfaces import UserRepository
from user_management_context.application.commands import CreateUserCommand
from user_management_context.application.use_cases import CreateUserUseCase
from user_management_context.domain.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
)

from user_management_context.application.interfaces.haching_gateway import (
    HashingGateway,
)
from shared_kernel.access_control import AccessController


@pytest.fixture
def use_case(
    user_repository: UserRepository,
    hash_gateway: HashingGateway,
    access_controller: AccessController,
):
    return CreateUserUseCase(user_repository, hash_gateway, access_controller)


def test_should_create_user(
    use_case: CreateUserUseCase,
    user_repository: UserRepository,
    hash_gateway: HashingGateway,
    access_controller: AccessController,
):
    requester_id = UUID("00000000-0000-0000-0000-000000000000")
    access_controller.grant_create_access(requester_id, user_repository.resource_id)

    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"
    expected_hashed_password = "hashed(securepassword123)"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, password=password
    )

    user_id = use_case.execute(requester_id, command)

    created_user = user_repository.get_by_id(user_id)
    assert created_user is not None
    assert created_user.id == uuid
    assert created_user.username == username
    assert created_user.email == email
    assert created_user.password_hashed == expected_hashed_password

    assert hash_gateway.compare(password, created_user.password_hashed) is True


def test_should_raise_not_existing_username(
    user_repository: UserRepository,
):
    with pytest.raises(UserNotFoundError) as _:
        user_repository.get_by_id(UUID("123e4567-e89b-12d3-a456-426614174000"))


def test_should_raise_when_user_already_exists(
    use_case: CreateUserUseCase,
    user_repository: UserRepository,
    access_controller: AccessController,
):
    requester_id = UUID("00000000-0000-0000-0000-000000000000")
    access_controller.grant_create_access(requester_id, user_repository.resource_id)

    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"
    command = CreateUserCommand(
        id=uuid, username=username, email=email, password=password
    )
    use_case.execute(requester_id, command)
    with pytest.raises(UserAlreadyExistsError) as _:
        use_case.execute(requester_id, command)
