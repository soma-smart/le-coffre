from uuid import UUID, uuid4

import pytest

from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.use_cases import CreateUserUseCase
from identity_access_management_context.domain.entities import PasswordCredentialRecord
from identity_access_management_context.domain.events import UserCreatedEvent
from identity_access_management_context.domain.exceptions import (
    EmailAlreadyUsedException,
)
from shared_kernel.adapters.primary.exceptions import NotAdminError
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects.constants import ADMIN_ROLE
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher

from ..fakes import (
    FakeGroupMemberRepository,
    FakeGroupRepository,
    FakePasswordCredentialRecordRepository,
    FakePasswordHashingGateway,
    FakeUserRepository,
)


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    password_hashing_gateway: FakePasswordHashingGateway,
    event_publisher,
    user_event_repository,
):
    return CreateUserUseCase(
        user_repository,
        password_credential_record_repository,
        group_repository,
        group_member_repository,
        password_hashing_gateway,
        event_publisher,
        user_event_repository,
    )


def test_given_valid_user_data_when_creating_user_should_create_user(
    use_case: CreateUserUseCase,
    user_repository: FakeUserRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        requesting_user=AuthenticatedUser(UUID("423e4567-e89b-12d3-a456-426614174000"), [ADMIN_ROLE]),
        id=uuid,
        username=username,
        email=email,
        name=name,
        password=password,
    )

    user_id = use_case.execute(command)

    created_user = user_repository.get_by_id(user_id)
    assert created_user is not None
    assert created_user.id == uuid
    assert created_user.username == username
    assert created_user.email == email
    assert created_user.name == name


def test_given_non_admin_user_when_creating_user_should_raise_not_admin_error(
    use_case: CreateUserUseCase,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        requesting_user=AuthenticatedUser(UUID("423e4567-e89b-12d3-a456-426614174000"), []),
        id=uuid,
        username=username,
        email=email,
        name=name,
        password=password,
    )

    with pytest.raises(NotAdminError):
        use_case.execute(command)


def test_given_user_with_password_when_creating_user_should_store_hashed_password(
    use_case: CreateUserUseCase,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        requesting_user=AuthenticatedUser(UUID("423e4567-e89b-12d3-a456-426614174000"), [ADMIN_ROLE]),
        id=uuid,
        username=username,
        email=email,
        name=name,
        password=password,
    )

    user_id = use_case.execute(command)

    (created_credential,) = password_credential_record_repository.list_by_principal_id(user_id)
    assert created_credential.principal_id == user_id
    assert created_credential.email == email
    assert created_credential.password_hash == b"hashed(secure_password123)"


def test_given_existing_user_when_creating_it_again_should_refuse_its_email(
    use_case: CreateUserUseCase,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        requesting_user=AuthenticatedUser(UUID("423e4567-e89b-12d3-a456-426614174000"), [ADMIN_ROLE]),
        id=uuid,
        username=username,
        email=email,
        name=name,
        password=password,
    )

    use_case.execute(command)
    with pytest.raises(EmailAlreadyUsedException):
        use_case.execute(command)


def test_given_new_user_when_creating_user_should_create_personal_group(
    use_case: CreateUserUseCase,
    group_repository: FakeGroupRepository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    username = "testuser"
    email = "testuser@example.com"
    name = "Test User"
    password = "secure_password123"

    command = CreateUserCommand(
        requesting_user=AuthenticatedUser(UUID("423e4567-e89b-12d3-a456-426614174000"), [ADMIN_ROLE]),
        id=uuid,
        username=username,
        email=email,
        name=name,
        password=password,
    )

    user_id = use_case.execute(command)

    personal_group = group_repository.get_by_principal_id(user_id)
    assert personal_group is not None
    assert personal_group.principal_id == user_id
    assert personal_group.name == f"{username}'s Personal Group"


def test_given_valid_user_data_when_creating_user_should_publish_user_created_event(
    use_case: CreateUserUseCase,
    event_publisher: FakeDomainEventPublisher,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_id = UUID("423e4567-e89b-12d3-a456-426614174000")
    command = CreateUserCommand(
        requesting_user=AuthenticatedUser(admin_id, [ADMIN_ROLE]),
        id=uuid,
        username="testuser",
        email="testuser@example.com",
        name="Test User",
        password="secure_password123",
    )

    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(UserCreatedEvent)
    assert len(events) == 1
    assert events[0].user_id == uuid
    assert events[0].username == "testuser"
    assert events[0].email == "testuser@example.com"
    assert events[0].created_by_principal_id == admin_id


def test_given_valid_user_data_when_creating_user_should_store_user_created_event(
    use_case: CreateUserUseCase,
    user_event_repository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_id = UUID("423e4567-e89b-12d3-a456-426614174000")
    command = CreateUserCommand(
        requesting_user=AuthenticatedUser(admin_id, [ADMIN_ROLE]),
        id=uuid,
        username="testuser",
        email="testuser@example.com",
        name="Test User",
        password="secure_password123",
    )

    use_case.execute(command)

    assert len(user_event_repository.events) == 1
    stored = user_event_repository.events[0]
    assert stored["event_type"] == "UserCreatedEvent"
    assert stored["actor_principal_id"] == admin_id


def _create_command(email: str, user_id: UUID | None = None) -> CreateUserCommand:
    return CreateUserCommand(
        requesting_user=AuthenticatedUser(UUID("423e4567-e89b-12d3-a456-426614174000"), [ADMIN_ROLE]),
        id=user_id or uuid4(),
        username=email.split("@")[0],
        email=email,
        name="Someone",
        password="secure_password123",
    )


def test_given_an_email_used_by_another_user_when_creating_a_user_should_refuse_before_writing_anything(
    use_case: CreateUserUseCase,
    user_repository: FakeUserRepository,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    use_case.execute(_create_command("taken@example.com"))
    newcomer = _create_command("taken@example.com")

    with pytest.raises(EmailAlreadyUsedException):
        use_case.execute(newcomer)

    assert user_repository.get_by_id(newcomer.id) is None
    assert password_credential_record_repository.list_by_principal_id(newcomer.id) == []


def test_given_an_email_used_to_sign_in_by_another_user_when_creating_a_user_should_refuse_it(
    use_case: CreateUserUseCase,
    password_credential_record_repository: FakePasswordCredentialRecordRepository,
):
    password_credential_record_repository.save(
        PasswordCredentialRecord(principal_id=uuid4(), email="signin@example.com", password_hash=b"hash")
    )

    with pytest.raises(EmailAlreadyUsedException):
        use_case.execute(_create_command("signin@example.com"))
