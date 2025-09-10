from uuid import UUID
import pytest

from user_management_context.application.use_cases import GetUserUseCase
from user_management_context.application.gateways import UserRepository
from user_management_context.domain.entities import User


@pytest.fixture
def use_case(user_repository: UserRepository):
    return GetUserUseCase(user_repository)


def test_should_get_user_by_id(
  use_case: GetUserUseCase,
  user_repository: UserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"

    user = User(
        id=uuid, username=username, email=email, password_hashed=password
    )
    user_repository.save(user)

    retrieved_user = use_case.execute(uuid)

    assert retrieved_user is not None
    assert retrieved_user.id == uuid
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert retrieved_user.password_hashed == "securepassword123"


def test_should_get_user_by_email(
  use_case: GetUserUseCase,
  user_repository: UserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    password = "securepassword123"

    user = User(
        id=uuid, username=username, email=email, password_hashed=password
    )
    user_repository.save(user)

    retrieved_user = use_case.execute_by_email(email)
    assert retrieved_user is not None
    assert retrieved_user.id == uuid
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert retrieved_user.password_hashed == "securepassword123"
