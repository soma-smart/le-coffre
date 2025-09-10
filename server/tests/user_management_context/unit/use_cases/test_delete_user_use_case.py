from uuid import UUID
import pytest
from user_management_context.application.commands import CreateUserCommand
from user_management_context.application.gateways import UserRepository
from user_management_context.adapters.secondary.gateways import (
  InMemoryUserRepository
)
from user_management_context.application.use_cases import (
  DeleteUserUseCase
)
from user_management_context.domain.exceptions import (
  UserNotFoundError
)


@pytest.fixture
def use_case(
  user_repository: UserRepository,
):
    return DeleteUserUseCase(user_repository)


def test_should_delete_user(
  use_case: DeleteUserUseCase,
  user_repository: InMemoryUserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, password=password
    )
    user_repository.save(command)

    use_case.execute(uuid)

    with pytest.raises(UserNotFoundError) as _:
        user_repository.get_by_id(uuid)
