from uuid import UUID
import pytest
from identity_access_management_context.application.use_cases import UpdateUserUseCase

from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.events import UserUpdatedEvent
from identity_access_management_context.application.commands import UpdateUserCommand
from shared_kernel.domain.entities import AuthenticatedUser
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from ..fakes import FakeUserRepository


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    event_publisher,
    user_event_repository,
):
    return UpdateUserUseCase(user_repository, event_publisher, user_event_repository)


def test_given_valid_update_data_when_updating_user_should_persist_changes(
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

    requesting_user = AuthenticatedUser(user_id=uuid, roles=[])
    command = UpdateUserCommand(
        requesting_user=requesting_user,
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


def test_given_valid_update_data_when_updating_user_should_publish_user_updated_event(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    event_publisher: FakeDomainEventPublisher,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(id=uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    requesting_user = AuthenticatedUser(user_id=uuid, roles=[])
    command = UpdateUserCommand(
        requesting_user=requesting_user,
        id=uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(UserUpdatedEvent)
    assert len(events) == 1
    assert events[0].user_id == uuid
    assert events[0].updated_by_user_id == uuid


def test_given_valid_update_data_when_updating_user_should_store_user_updated_event(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    user_event_repository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(id=uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    requesting_user = AuthenticatedUser(user_id=uuid, roles=[])
    command = UpdateUserCommand(
        requesting_user=requesting_user,
        id=uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    assert len(user_event_repository.events) == 1
    stored = user_event_repository.events[0]
    assert stored["event_type"] == "UserUpdatedEvent"
    assert stored["actor_user_id"] == uuid
