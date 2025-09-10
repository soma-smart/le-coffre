from uuid import UUID
import pytest

from user_management_context.application.use_cases import GetUserUseCase
from user_management_context.adapters.secondary.gateways import (
  InMemoryUserRepository
)
from user_management_context.application.gateways import UserRepository
from user_management_context.application.commands import CreateUserCommand


@pytest.fixture
def use_case(user_repository: UserRepository):
    return GetUserUseCase(user_repository)


def test_should_get_user_by_id(
  use_case: GetUserUseCase,
  user_repository: InMemoryUserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, password=password
    )
    user_id = user_repository.save(command)

    retrieved_user = use_case.execute(user_id)

    assert retrieved_user is not None
    assert retrieved_user.id == uuid
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert retrieved_user.password_hashed == "hashed(securepassword123)"
