import pytest
from uuid import UUID

from identity_access_management_context.application.gateways import (
    UserRepository,
    UserPasswordRepository,
    GroupRepository,
)
from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.use_cases import CreateUserUseCase
from identity_access_management_context.domain.exceptions import (
    UserAlreadyExistsError,
)
from tests.identity_access_management_context.unit.fakes import (
    FakePasswordHashingGateway,
    FakeGroupMemberRepository,
)


@pytest.fixture
def use_case(
    user_repository: UserRepository,
    user_password_repository: UserPasswordRepository,
    group_repository: GroupRepository,
):
    password_hashing_gateway = FakePasswordHashingGateway()
    group_member_repository = FakeGroupMemberRepository()
    return CreateUserUseCase(
        user_repository,
        user_password_repository,
        group_repository,
        group_member_repository,
        password_hashing_gateway,
    )


def test_should_create_user(
    use_case: CreateUserUseCase,
    user_repository: UserRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, name=name, password=password
    )

    user_id = use_case.execute(command)

    created_user = user_repository.get_by_id(user_id)
    assert created_user is not None
    assert created_user.id == uuid
    assert created_user.username == username
    assert created_user.email == email
    assert created_user.name == name


def test_should_create_user_password(
    use_case: CreateUserUseCase,
    user_password_repository: UserPasswordRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, name=name, password=password
    )

    user_id = use_case.execute(command)

    created_user_password = user_password_repository.get_by_id(user_id)
    assert created_user_password is not None
    assert created_user_password.id == user_id
    assert created_user_password.email == email
    assert created_user_password.password_hash == b"hashed(secure_password123)"
    assert created_user_password.display_name == name


def test_should_raise_when_user_already_exists(
    use_case: CreateUserUseCase,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, name=name, password=password
    )

    use_case.execute(command)
    with pytest.raises(UserAlreadyExistsError) as _:
        use_case.execute(command)


def test_should_create_personal_group_when_creating_user(
    use_case: CreateUserUseCase,
    group_repository: GroupRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        id=uuid, username=username, email=email, name=name, password=password
    )

    user_id = use_case.execute(command)

    personal_group = group_repository.get_by_user_id(user_id)
    assert personal_group is not None
    assert personal_group.user_id == user_id
    assert personal_group.name == f"{username}'s Personal Group"
