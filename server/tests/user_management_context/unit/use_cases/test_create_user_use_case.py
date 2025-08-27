import pytest
from uuid import UUID

from user_management_context.application.gateways import UserRepository
from user_management_context.application.commands import CreateUserCommand
from user_management_context.application.use_cases import (
  CreateUserUseCase,
  HashingService
)


@pytest.fixture
def use_case(
  user_repository: UserRepository,
  hash_password_service: HashingService
):
    return CreateUserUseCase(user_repository, hash_password_service)


def test_should_create_user(
  use_case: CreateUserUseCase,
  user_repository: UserRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"
    expected_hashed_password = "hashed(securepassword123)"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, password=password
    )

    user_id = use_case.execute(command)

    created_user = user_repository.get_by_id(user_id)
    assert created_user is not None
    assert created_user.id == uuid
    assert created_user.username == username
    assert created_user.email == email
    assert created_user.password_hashed == expected_hashed_password
