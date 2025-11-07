from uuid import UUID
import pytest

from identity_access_management_context.application.use_cases import GetUserUseCase
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User


@pytest.fixture
def use_case(user_repository: UserRepository):
    return GetUserUseCase(user_repository)


def test_should_get_user_by_id(
    use_case: GetUserUseCase, user_repository: UserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "User"

    user = User(id=uuid, username=username, email=email, name=name)
    user_repository.save(user)

    retrieved_user = use_case.execute(user_id=uuid)

    assert retrieved_user is not None
    assert retrieved_user.id == uuid
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert retrieved_user.name == name


def test_should_get_user_by_email(
    use_case: GetUserUseCase, user_repository: UserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "User"

    user = User(id=uuid, username=username, email=email, name=name)
    user_repository.save(user)

    retrieved_user = use_case.execute(user_email=email)
    assert retrieved_user is not None
    assert retrieved_user.id == uuid
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert retrieved_user.name == name


def test_should_raise_not_args_to_get_user(
    use_case: GetUserUseCase,
):
    with pytest.raises(ValueError) as _:
        use_case.execute()
