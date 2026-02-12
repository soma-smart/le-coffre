import pytest
from uuid import UUID

from identity_access_management_context.application.commands import (
    AddUserToGroupCommand,
)
from identity_access_management_context.application.use_cases import (
    AddUserToGroupUseCase,
)
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
)
from identity_access_management_context.domain.entities import User, Group
from identity_access_management_context.domain.events import UserAddedToGroupEvent
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from ..fakes import FakeUserRepository, FakeGroupRepository, FakeGroupMemberRepository


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    event_publisher,
    iam_event_repository,
):
    return AddUserToGroupUseCase(
        user_repository=user_repository,
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        event_publisher=event_publisher,
        iam_event_repository=iam_event_repository,
    )


def test_given_owner_when_adding_user_to_group_then_user_is_added_as_member(
    use_case: AddUserToGroupUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    new_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    new_user = User(
        id=new_user_id,
        username="newuser",
        email="newuser@example.com",
        name="New User",
    )
    user_repository.save(owner)
    user_repository.save(new_user)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = AddUserToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=new_user_id,
    )

    use_case.execute(command)

    assert group_member_repository.is_member(group_id, new_user_id)
    assert not group_member_repository.is_owner(group_id, new_user_id)


def test_given_non_owner_when_adding_user_to_group_then_raise_user_not_owner_exception(
    use_case: AddUserToGroupUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    non_owner_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    new_user_id = UUID("423e4567-e89b-12d3-a456-426614174003")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    non_owner = User(
        id=non_owner_id,
        username="nonowner",
        email="nonowner@example.com",
        name="Non Owner User",
    )
    new_user = User(
        id=new_user_id,
        username="newuser",
        email="newuser@example.com",
        name="New User",
    )
    user_repository.save(owner)
    user_repository.save(non_owner)
    user_repository.save(new_user)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = AddUserToGroupCommand(
        requester_id=non_owner_id,
        group_id=group_id,
        user_id=new_user_id,
    )

    with pytest.raises(UserNotOwnerOfGroupException):
        use_case.execute(command)


def test_given_group_not_found_when_adding_user_then_raise_group_not_found_exception(
    use_case: AddUserToGroupUseCase,
    user_repository: FakeUserRepository,
):
    requester_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    nonexistent_group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    user_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    requester = User(
        id=requester_id,
        username="requester",
        email="requester@example.com",
        name="Requester User",
    )
    user = User(
        id=user_id,
        username="user",
        email="user@example.com",
        name="User",
    )
    user_repository.save(requester)
    user_repository.save(user)

    command = AddUserToGroupCommand(
        requester_id=requester_id,
        group_id=nonexistent_group_id,
        user_id=user_id,
    )

    with pytest.raises(GroupNotFoundException):
        use_case.execute(command)


def test_given_user_not_found_when_adding_to_group_then_raise_user_not_found_exception(
    use_case: AddUserToGroupUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    nonexistent_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    user_repository.save(owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = AddUserToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=nonexistent_user_id,
    )

    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_personal_group_when_adding_user_then_raise_cannot_modify_personal_group_exception(
    use_case: AddUserToGroupUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    new_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    new_user = User(
        id=new_user_id,
        username="newuser",
        email="newuser@example.com",
        name="New User",
    )
    user_repository.save(owner)
    user_repository.save(new_user)

    personal_group = Group(id=group_id, name="Owner's Personal Group", is_personal=True)
    group_repository.save_group(personal_group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = AddUserToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=new_user_id,
    )

    with pytest.raises(CannotModifyPersonalGroupException):
        use_case.execute(command)


def test_given_user_already_member_when_adding_then_do_nothing(
    use_case: AddUserToGroupUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    existing_member_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    existing_member = User(
        id=existing_member_id,
        username="member",
        email="member@example.com",
        name="Member User",
    )
    user_repository.save(owner)
    user_repository.save(existing_member)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, existing_member_id, is_owner=False)

    command = AddUserToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=existing_member_id,
    )

    use_case.execute(command)

    assert group_member_repository.is_member(group_id, existing_member_id)
    assert not group_member_repository.is_owner(group_id, existing_member_id)


def test_given_owner_when_adding_user_to_group_then_should_publish_user_added_to_group_event(
    use_case: AddUserToGroupUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    event_publisher: FakeDomainEventPublisher,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    new_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(id=owner_id, username="owner", email="owner@example.com", name="Owner User")
    new_user = User(id=new_user_id, username="newuser", email="newuser@example.com", name="New User")
    user_repository.save(owner)
    user_repository.save(new_user)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = AddUserToGroupCommand(requester_id=owner_id, group_id=group_id, user_id=new_user_id)
    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(UserAddedToGroupEvent)
    assert len(events) == 1
    assert events[0].group_id == group_id
    assert events[0].user_id == new_user_id
    assert events[0].added_by_user_id == owner_id
