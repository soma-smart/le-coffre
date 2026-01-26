from uuid import UUID
import pytest
from identity_access_management_context.application.commands import ListUserCommand
from identity_access_management_context.application.use_cases import ListUserUseCase

from identity_access_management_context.domain.entities import User
from ..fakes import FakeUserRepository
from shared_kernel.authentication import AuthenticatedUser


@pytest.fixture
def use_case(user_repository: FakeUserRepository):
    return ListUserUseCase(user_repository)


def test_should_list_users_when_admin(
    use_case: ListUserUseCase, user_repository: FakeUserRepository
):
    admin_user = AuthenticatedUser(
        user_id=UUID("999e4567-e89b-12d3-a456-426614174999"), roles=["admin"]
    )

    user1 = User(
        id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        username="user1",
        email="user1@example.com",
        name="User",
    )
    user2 = User(
        id=UUID("223e4567-e89b-12d3-a456-426614174001"),
        username="user2",
        email="user2@example.com",
        name="Other User",
    )

    user_repository.save(user1)
    user_repository.save(user2)

    command = ListUserCommand(requesting_user=admin_user)
    users = use_case.execute(command)
    assert len(users) == 2
    assert any(user.username == "user1" for user in users)
    assert any(user.username == "user2" for user in users)
