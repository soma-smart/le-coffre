from uuid import UUID
import pytest
from identity_access_management_context.application.use_cases import DeleteUserUseCase
from identity_access_management_context.application.commands import DeleteUserCommand
from identity_access_management_context.domain.entities import (
    User,
    Group,
    PersonalGroup,
)
from identity_access_management_context.domain.events import UserDeletedEvent
from ..fakes import FakeUserRepository, FakeGroupRepository, FakeGroupMemberRepository
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.adapters.primary.exceptions import NotAdminError
from tests.fakes import FakeDomainEventPublisher


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    return DeleteUserUseCase(
        user_repository,
        group_repository,
        group_member_repository,
        domain_event_publisher,
    )


def test_given_admin_user_when_deleting_user_should_remove_user(
    use_case: DeleteUserUseCase, user_repository: FakeUserRepository
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


def test_given_non_admin_user_when_deleting_user_should_raise_not_admin_error(
    use_case: DeleteUserUseCase, user_repository: FakeUserRepository
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


def test_given_admin_user_when_deleting_user_should_publish_user_deleted_event(
    use_case: DeleteUserUseCase,
    user_repository: FakeUserRepository,
    domain_event_publisher: FakeDomainEventPublisher,
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

    assert len(domain_event_publisher.published_events) == 1
    published_event = domain_event_publisher.published_events[0]
    assert isinstance(published_event, UserDeletedEvent)
    assert published_event.user_id == user_uuid
    assert published_event.deleted_by_user_id == admin_uuid


def test_given_user_in_multiple_groups_when_deleting_user_should_remove_from_all_groups(
    use_case: DeleteUserUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    user_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")
    group1_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group2_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    personal_group_id = UUID("423e4567-e89b-12d3-a456-426614174003")

    user = User(
        id=user_uuid, username="testuser", email="test@example.com", name="User"
    )
    user_repository.save(user)

    group1 = Group(id=group1_id, name="Group 1", is_personal=False)
    group2 = Group(id=group2_id, name="Group 2", is_personal=False)
    personal_group = PersonalGroup(
        id=personal_group_id, name="Personal", user_id=user_uuid
    )

    group_repository.save_group(group1)
    group_repository.save_group(group2)
    group_repository.save_personal_group(personal_group)

    group_member_repository.add_member(group1_id, user_uuid, is_owner=False)
    group_member_repository.add_member(group2_id, user_uuid, is_owner=False)
    group_member_repository.add_member(personal_group_id, user_uuid, is_owner=True)

    admin_user = AuthenticatedUser(user_id=admin_uuid, roles=["admin"])
    command = DeleteUserCommand(user_id=user_uuid, requesting_user=admin_user)

    use_case.execute(command)

    assert not group_member_repository.is_member(group1_id, user_uuid)
    assert not group_member_repository.is_member(group2_id, user_uuid)
    assert user_repository.get_by_id(user_uuid) is None


def test_given_user_with_personal_group_when_deleting_user_should_delete_personal_group(
    use_case: DeleteUserUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    user_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")
    personal_group_id = UUID("423e4567-e89b-12d3-a456-426614174003")

    user = User(
        id=user_uuid, username="testuser", email="test@example.com", name="User"
    )
    user_repository.save(user)

    personal_group = PersonalGroup(
        id=personal_group_id, name="Personal", user_id=user_uuid
    )
    group_repository.save_personal_group(personal_group)
    group_member_repository.add_member(personal_group_id, user_uuid, is_owner=True)

    admin_user = AuthenticatedUser(user_id=admin_uuid, roles=["admin"])
    command = DeleteUserCommand(user_id=user_uuid, requesting_user=admin_user)

    use_case.execute(command)

    assert user_repository.get_by_id(user_uuid) is None
    assert group_repository.get_by_id(personal_group_id) is None


def test_given_user_owner_of_shared_group_when_deleting_user_should_delete_group_if_sole_owner(
    use_case: DeleteUserUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    user_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    user = User(
        id=user_uuid, username="testuser", email="test@example.com", name="User"
    )
    user_repository.save(user)

    group = Group(id=group_id, name="Shared Group", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, user_uuid, is_owner=True)

    admin_user = AuthenticatedUser(user_id=admin_uuid, roles=["admin"])
    command = DeleteUserCommand(user_id=user_uuid, requesting_user=admin_user)

    use_case.execute(command)

    assert user_repository.get_by_id(user_uuid) is None
    assert group_repository.get_by_id(group_id) is None


def test_given_user_owner_of_shared_group_when_deleting_user_should_keep_group_if_other_owners_exist(
    use_case: DeleteUserUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    user_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")
    other_owner_uuid = UUID("523e4567-e89b-12d3-a456-426614174005")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    user = User(
        id=user_uuid, username="testuser", email="test@example.com", name="User"
    )
    user_repository.save(user)

    group = Group(id=group_id, name="Shared Group", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, user_uuid, is_owner=True)
    group_member_repository.add_member(group_id, other_owner_uuid, is_owner=True)

    admin_user = AuthenticatedUser(user_id=admin_uuid, roles=["admin"])
    command = DeleteUserCommand(user_id=user_uuid, requesting_user=admin_user)

    use_case.execute(command)

    assert user_repository.get_by_id(user_uuid) is None
    assert group_repository.get_by_id(group_id) is not None
    assert not group_member_repository.is_member(group_id, user_uuid)


def test_given_user_when_deleting_should_publish_event_with_personal_group_id(
    use_case: DeleteUserUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    domain_event_publisher: FakeDomainEventPublisher,
):
    user_uuid = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_uuid = UUID("123e4567-e89b-12d3-a456-426614174001")
    personal_group_id = UUID("423e4567-e89b-12d3-a456-426614174003")

    user = User(
        id=user_uuid, username="testuser", email="test@example.com", name="User"
    )
    user_repository.save(user)

    personal_group = PersonalGroup(
        id=personal_group_id, name="Personal", user_id=user_uuid
    )
    group_repository.save_personal_group(personal_group)
    group_member_repository.add_member(personal_group_id, user_uuid, is_owner=True)

    admin_user = AuthenticatedUser(user_id=admin_uuid, roles=["admin"])
    command = DeleteUserCommand(user_id=user_uuid, requesting_user=admin_user)

    use_case.execute(command)

    assert len(domain_event_publisher.published_events) == 1
    published_event = domain_event_publisher.published_events[0]
    assert isinstance(published_event, UserDeletedEvent)
    assert published_event.user_id == user_uuid
    assert published_event.deleted_by_user_id == admin_uuid
    assert published_event.personal_group_id == personal_group_id
