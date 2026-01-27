from uuid import UUID
import pytest

from identity_access_management_context.application.commands import GetUserCommand
from identity_access_management_context.application.use_cases import GetUserUseCase
from identity_access_management_context.domain.entities import User
from ..fakes import FakeUserRepository


@pytest.fixture
def use_case(user_repository: FakeUserRepository):
    return GetUserUseCase(user_repository)


def test_given_user_id_when_getting_user_should_return_user_by_id(
    use_case: GetUserUseCase, user_repository: FakeUserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "User"

    user = User(id=uuid, username=username, email=email, name=name)
    user_repository.save(user)

    command = GetUserCommand(user_id=uuid)
    retrieved_user = use_case.execute(command)

    assert retrieved_user is not None
    assert retrieved_user.id == uuid
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert retrieved_user.name == name


def test_given_user_email_when_getting_user_should_return_user_by_email(
    use_case: GetUserUseCase, user_repository: FakeUserRepository
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "User"

    user = User(id=uuid, username=username, email=email, name=name)
    user_repository.save(user)

    command = GetUserCommand(user_email=email)
    retrieved_user = use_case.execute(command)
    assert retrieved_user is not None
    assert retrieved_user.id == uuid
    assert retrieved_user.username == username
    assert retrieved_user.email == email
    assert retrieved_user.name == name


def test_given_no_arguments_when_getting_user_should_raise_value_error(
    use_case: GetUserUseCase,
):
    command = GetUserCommand()
    with pytest.raises(ValueError) as _:
        use_case.execute(command)
