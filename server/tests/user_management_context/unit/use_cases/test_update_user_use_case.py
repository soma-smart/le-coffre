from uuid import UUID
import pytest
from user_management_context.application.use_cases import UpdateUserUseCase
from user_management_context.application.gateways import UserRepository
from user_management_context.domain.entities import User
from user_management_context.application.commands import UpdateUserCommand
from user_management_context.application.gateways.haching_gateway import (
  HashingGateway
)


@pytest.fixture
def use_case(
  user_repository: UserRepository,
  hash_gateway: HashingGateway,
):
    return UpdateUserUseCase(user_repository, hash_gateway)


def test_should_update_user(
  use_case: UpdateUserUseCase,
  user_repository: UserRepository,
  hash_gateway: HashingGateway,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"

    user = User(
        id=uuid, username=username, email=email, password_hashed=password
    )
    user_repository.save(user)

    new_username = "updateduser"
    new_email = "updateduser@example.com"
    new_password = "newsecurepassword456"
    expected_hashed_password = "hashed(newsecurepassword456)"

    command = UpdateUserCommand(
        username=new_username,
        email=new_email,
        password=new_password,
    )

    use_case.execute(uuid, command)
    updated_user = user_repository.get_by_id(uuid)
    assert updated_user is not None
    assert updated_user.id == uuid
    assert updated_user.username == new_username
    assert updated_user.email == new_email
    assert updated_user.password_hashed == expected_hashed_password
