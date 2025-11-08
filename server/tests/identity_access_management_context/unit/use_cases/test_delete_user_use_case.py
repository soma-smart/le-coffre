from uuid import UUID
import pytest
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.adapters.secondary import InMemoryUserRepository
from identity_access_management_context.application.use_cases import DeleteUserUseCase
from identity_access_management_context.application.commands import DeleteUserCommand
from identity_access_management_context.domain.exceptions import UserNotFoundError
from identity_access_management_context.domain.entities import User
from identity_access_management_context.adapters.primary.dependencies import (
    AuthenticatedUser,
    NotAdminError,
)


@pytest.fixture
def use_case(
    user_repository: UserRepository,
):
    return DeleteUserUseCase(user_repository)


def test_when_admin_should_delete_user(
    use_case: DeleteUserUseCase, user_repository: InMemoryUserRepository
):
    user_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")
    username = "testuser"
    email = "testuser@example.com"
    name = "User"

    user = User(id=user_uuid, username=username, email=email, name=name)
    user_repository.save(user)

    admin_user = AuthenticatedUser(user_id=admin_uuid, roles=["admin"])

    command = DeleteUserCommand(user_id=user_uuid, requesting_user=admin_user)

    use_case.execute(command)

    assert user_repository.get_by_id(user_uuid) is None


def test_should_raise_not_admin_error_when_requesting_user_is_not_admin(
    use_case: DeleteUserUseCase, user_repository: InMemoryUserRepository
):
    user_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    regular_user_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")

    user = User(
        id=user_uuid, username="testuser", email="test@example.com", name="User"
    )
    user_repository.save(user)

    regular_user = AuthenticatedUser(user_id=regular_user_uuid, roles=[])

    command = DeleteUserCommand(user_id=user_uuid, requesting_user=regular_user)

    with pytest.raises(NotAdminError):
        use_case.execute(command)
