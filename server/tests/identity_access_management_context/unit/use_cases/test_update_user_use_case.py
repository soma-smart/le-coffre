from uuid import UUID
import pytest
from identity_access_management_context.application.use_cases import UpdateUserUseCase

from identity_access_management_context.domain.entities import User
from identity_access_management_context.application.commands import UpdateUserCommand
from ..fakes import FakeUserRepository


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
):
    return UpdateUserUseCase(user_repository)


def test_should_update_user(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "User"

    user = User(id=uuid, username=username, email=email, name=name)
    user_repository.save(user)

    new_username = "updateduser"
    new_email = "updateduser@example.com"
    new_name = "New User"

    command = UpdateUserCommand(
        id=uuid,
        username=new_username,
        email=new_email,
        name=new_name,
    )

    use_case.execute(command)
    updated_user = user_repository.get_by_id(uuid)
    assert updated_user is not None
    assert updated_user.id == uuid
    assert updated_user.username == new_username
    assert updated_user.email == new_email
    assert updated_user.name == new_name
