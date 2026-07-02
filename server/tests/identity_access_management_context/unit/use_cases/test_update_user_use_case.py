from uuid import UUID

import pytest

from identity_access_management_context.application.commands import UpdateUserCommand
from identity_access_management_context.application.use_cases import UpdateUserUseCase
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.events import UserUpdatedEvent
from identity_access_management_context.domain.exceptions import UserUpdateNotAllowedException
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


def test_given_user_updating_own_profile_when_updating_should_persist_changes(
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
        requesting_user=AuthenticatedUser(user_id=uuid, roles=[]),
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


def test_given_admin_updating_another_user_when_updating_should_persist_changes(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    target_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")

    user = User(id=target_uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=admin_uuid, roles=["admin"]),
        id=target_uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    updated_user = user_repository.get_by_id(target_uuid)
    assert updated_user is not None
    assert updated_user.username == "updateduser"
    assert updated_user.email == "updateduser@example.com"
    assert updated_user.name == "New User"


def test_given_non_admin_updating_another_user_when_updating_should_raise_user_update_not_allowed(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
):
    target_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    other_uuid = UUID("123e4567-e89b-12d3-a456-426614174002")

    user = User(id=target_uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=other_uuid, roles=[]),
        id=target_uuid,
        username="hacked",
        email="hacked@example.com",
        name="Hacked",
    )

    with pytest.raises(UserUpdateNotAllowedException):
        use_case.execute(command)

    unchanged_user = user_repository.get_by_id(target_uuid)
    assert unchanged_user is not None
    assert unchanged_user.username == "testuser"
    assert unchanged_user.email == "testuser@example.com"
    assert unchanged_user.name == "User"


def test_given_user_updating_own_profile_when_updating_should_publish_user_updated_event(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    event_publisher: FakeDomainEventPublisher,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(id=uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=uuid, roles=[]),
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


def test_given_admin_updating_another_user_when_updating_should_record_admin_as_actor(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    event_publisher: FakeDomainEventPublisher,
    user_event_repository,
):
    target_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")

    user = User(id=target_uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=admin_uuid, roles=["admin"]),
        id=target_uuid,
        username="updateduser",
        email="updateduser@example.com",
        name="New User",
    )

    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(UserUpdatedEvent)
    assert len(events) == 1
    assert events[0].user_id == target_uuid
    assert events[0].updated_by_user_id == admin_uuid

    assert len(user_event_repository.events) == 1
    assert user_event_repository.events[0]["actor_user_id"] == admin_uuid


def test_given_user_updating_own_profile_when_updating_should_store_user_updated_event(
    use_case: UpdateUserUseCase,
    user_repository: FakeUserRepository,
    user_event_repository,
):
    uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    user = User(id=uuid, username="testuser", email="testuser@example.com", name="User")
    user_repository.save(user)

    command = UpdateUserCommand(
        requesting_user=AuthenticatedUser(user_id=uuid, roles=[]),
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
