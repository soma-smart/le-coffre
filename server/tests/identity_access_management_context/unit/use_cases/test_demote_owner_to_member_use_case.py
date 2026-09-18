from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    DemoteOwnerToMemberCommand,
)
from identity_access_management_context.application.use_cases import (
    DemoteOwnerToMemberUseCase,
)
from identity_access_management_context.domain.entities import Group, User
from identity_access_management_context.domain.events import OwnerDemotedToMemberEvent
from identity_access_management_context.domain.exceptions import (
    CannotDemoteLastOwnerException,
    CannotModifyPersonalGroupException,
    GroupNotFoundException,
    UserNotFoundException,
    UserNotMemberOfGroupException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher

from ..fakes import FakeGroupMemberRepository, FakeGroupRepository, FakeUserRepository


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    event_publisher,
    group_event_repository,
):
    return DemoteOwnerToMemberUseCase(
        user_repository=user_repository,
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        event_publisher=event_publisher,
        group_event_repository=group_event_repository,
    )


def test_given_owner_when_demoting_co_owner_then_co_owner_becomes_member(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    co_owner_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    co_owner = User(id=co_owner_id, username="coowner", email="coowner@example.com", name="Co Owner User")
    user_repository.save(owner)
    user_repository.save(co_owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, co_owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]),
        group_id=group_id,
        user_id=co_owner_id,
    )

    use_case.execute(command)

    assert not group_member_repository.is_owner(group_id, co_owner_id)
    assert group_member_repository.is_member(group_id, co_owner_id)


def test_given_owner_when_demoting_self_then_becomes_member(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    co_owner_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    co_owner = User(id=co_owner_id, username="coowner", email="coowner@example.com", name="Co Owner User")
    user_repository.save(owner)
    user_repository.save(co_owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, co_owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]),
        group_id=group_id,
        user_id=owner_id,
    )

    use_case.execute(command)

    assert not group_member_repository.is_owner(group_id, owner_id)
    assert group_member_repository.is_member(group_id, owner_id)


def test_given_sole_owner_when_demoting_self_then_raise_cannot_demote_last_owner_exception(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    user_repository.save(owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]),
        group_id=group_id,
        user_id=owner_id,
    )

    with pytest.raises(CannotDemoteLastOwnerException):
        use_case.execute(command)

    assert group_member_repository.is_owner(group_id, owner_id)


def test_given_non_owner_when_demoting_owner_then_raise_user_not_owner_exception(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    non_owner_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    non_owner = User(id=non_owner_id, username="nonowner", email="nonowner@example.com", name="Non Owner User")
    user_repository.save(owner)
    user_repository.save(non_owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, non_owner_id, is_owner=False)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=non_owner_id, roles=[]),
        group_id=group_id,
        user_id=owner_id,
    )

    with pytest.raises(UserNotOwnerOfGroupException):
        use_case.execute(command)


def test_given_admin_not_owner_when_demoting_owner_then_owner_becomes_member(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    admin_id = UUID("523e4567-e89b-12d3-a456-426614174004")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    owner_id = UUID("623e4567-e89b-12d3-a456-426614174005")
    co_owner_id = UUID("723e4567-e89b-12d3-a456-426614174006")

    admin = User(id=admin_id, username="admin", email="admin@example.com", name="Admin User", roles=[ADMIN_ROLE])
    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    co_owner = User(id=co_owner_id, username="coowner", email="coowner@example.com", name="Co Owner User")
    user_repository.save(admin)
    user_repository.save(owner)
    user_repository.save(co_owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, co_owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=admin_id, roles=[ADMIN_ROLE]),
        group_id=group_id,
        user_id=owner_id,
    )

    use_case.execute(command)

    assert not group_member_repository.is_owner(group_id, owner_id)
    assert group_member_repository.is_member(group_id, owner_id)


def test_given_group_not_found_when_demoting_owner_then_raise_group_not_found_exception(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
):
    requester_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    nonexistent_group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    requester = User(id=requester_id, username="requester", email="requester@example.com", name="Requester User")
    user_repository.save(requester)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=requester_id, roles=[]),
        group_id=nonexistent_group_id,
        user_id=requester_id,
    )

    with pytest.raises(GroupNotFoundException):
        use_case.execute(command)


def test_given_personal_group_when_demoting_owner_then_raise_cannot_modify_personal_group_exception(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    user_repository.save(owner)

    group = Group(id=group_id, name="Personal Group", is_personal=True, user_id=owner_id)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]),
        group_id=group_id,
        user_id=owner_id,
    )

    with pytest.raises(CannotModifyPersonalGroupException):
        use_case.execute(command)


def test_given_user_not_found_when_demoting_owner_then_raise_user_not_found_exception(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    nonexistent_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    user_repository.save(owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]),
        group_id=group_id,
        user_id=nonexistent_user_id,
    )

    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_user_not_member_when_demoting_owner_then_raise_user_not_member_exception(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    non_member_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    non_member = User(
        id=non_member_id,
        username="nonmember",
        email="nonmember@example.com",
        name="Non Member User",
    )
    user_repository.save(owner)
    user_repository.save(non_member)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]),
        group_id=group_id,
        user_id=non_member_id,
    )

    with pytest.raises(UserNotMemberOfGroupException):
        use_case.execute(command)


def test_given_owner_when_demoting_plain_member_then_operation_is_a_no_op(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    member_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    member = User(id=member_id, username="member", email="member@example.com", name="Member User")
    user_repository.save(owner)
    user_repository.save(member)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, member_id, is_owner=False)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]),
        group_id=group_id,
        user_id=member_id,
    )

    use_case.execute(command)

    assert group_member_repository.is_member(group_id, member_id)
    assert not group_member_repository.is_owner(group_id, member_id)


def test_given_owner_when_demoting_co_owner_then_should_publish_owner_demoted_to_member_event(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    event_publisher: FakeDomainEventPublisher,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    co_owner_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    co_owner = User(id=co_owner_id, username="coowner", email="coowner@example.com", name="Co Owner User")
    user_repository.save(owner)
    user_repository.save(co_owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, co_owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]), group_id=group_id, user_id=co_owner_id
    )
    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(OwnerDemotedToMemberEvent)
    assert len(events) == 1
    assert events[0].group_id == group_id
    assert events[0].user_id == co_owner_id
    assert events[0].demoted_by_user_id == owner_id


def test_given_owner_when_demoting_co_owner_then_should_store_owner_demoted_to_member_event(
    use_case: DemoteOwnerToMemberUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    group_event_repository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    co_owner_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    co_owner = User(id=co_owner_id, username="coowner", email="coowner@example.com", name="Co Owner User")
    user_repository.save(owner)
    user_repository.save(co_owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, co_owner_id, is_owner=True)

    command = DemoteOwnerToMemberCommand(
        requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]), group_id=group_id, user_id=co_owner_id
    )
    use_case.execute(command)

    assert len(group_event_repository.events) == 1
    stored = group_event_repository.events[0]
    assert stored["event_type"] == "OwnerDemotedToMemberEvent"
    assert stored["actor_user_id"] == owner_id
