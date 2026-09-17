from datetime import datetime
from uuid import UUID

import pytest

from identity_access_management_context.application.commands import (
    ListGroupEventsCommand,
)
from identity_access_management_context.application.use_cases import (
    ListGroupEventsUseCase,
)
from identity_access_management_context.domain.entities import Group, User
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.domain.entities import AuthenticatedUser

from ..fakes import FakeGroupEventRepository, FakeGroupMemberRepository, FakeGroupRepository, FakeUserRepository

ADMIN_USER = AuthenticatedUser(user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"])


@pytest.fixture
def use_case(
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    user_repository: FakeUserRepository,
    group_event_repository: FakeGroupEventRepository,
):
    return ListGroupEventsUseCase(
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        user_repository=user_repository,
        group_event_repository=group_event_repository,
    )


def _save_group_with_owner(group_repository: FakeGroupRepository, group_member_repository: FakeGroupMemberRepository):
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_repository.save_group(Group(id=group_id, name="Development Team", is_personal=False))
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    return group_id, owner_id


def test_given_owner_when_listing_group_events_then_events_are_returned(
    use_case: ListGroupEventsUseCase,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    user_repository: FakeUserRepository,
    group_event_repository: FakeGroupEventRepository,
):
    group_id, owner_id = _save_group_with_owner(group_repository, group_member_repository)
    new_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    user_repository.save(User(id=owner_id, username="owner", email="owner@example.com", name="Owner"))
    user_repository.save(User(id=new_user_id, username="newuser", email="newuser@example.com", name="New User"))

    group_event_repository.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="UserAddedToGroupEvent",
        occurred_on=datetime(2026, 2, 6, 10, 0, 0),
        actor_user_id=owner_id,
        event_data={"group_id": str(group_id), "user_id": str(new_user_id)},
    )

    response = use_case.execute(
        ListGroupEventsCommand(group_id=group_id, requesting_user=AuthenticatedUser(user_id=owner_id, roles=[]))
    )

    assert len(response.events) == 1
    event = response.events[0]
    assert event.event_type == "UserAddedToGroupEvent"
    assert event.actor_email == "owner@example.com"
    assert event.event_data["user_email"] == "newuser@example.com"


def test_given_admin_with_no_group_access_when_listing_group_events_then_events_are_returned(
    use_case: ListGroupEventsUseCase,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    group_event_repository: FakeGroupEventRepository,
):
    group_id, owner_id = _save_group_with_owner(group_repository, group_member_repository)

    group_event_repository.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="OwnerAddedToGroupEvent",
        occurred_on=datetime(2026, 2, 6, 10, 0, 0),
        actor_user_id=owner_id,
        event_data={"group_id": str(group_id), "user_id": str(owner_id)},
    )

    response = use_case.execute(ListGroupEventsCommand(group_id=group_id, requesting_user=ADMIN_USER))

    assert len(response.events) == 1


def test_given_plain_member_when_listing_group_events_then_raise_not_owner_exception(
    use_case: ListGroupEventsUseCase,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    group_id, _owner_id = _save_group_with_owner(group_repository, group_member_repository)
    member_id = UUID("423e4567-e89b-12d3-a456-426614174003")
    group_member_repository.add_member(group_id, member_id, is_owner=False)

    with pytest.raises(UserNotOwnerOfGroupException):
        use_case.execute(
            ListGroupEventsCommand(group_id=group_id, requesting_user=AuthenticatedUser(user_id=member_id, roles=[]))
        )


def test_given_group_not_found_when_listing_group_events_then_raise_group_not_found_exception(
    use_case: ListGroupEventsUseCase,
):
    with pytest.raises(GroupNotFoundException):
        use_case.execute(
            ListGroupEventsCommand(
                group_id=UUID("00000000-0000-0000-0000-000000000000"),
                requesting_user=ADMIN_USER,
            )
        )


def test_given_event_types_filter_when_listing_group_events_then_only_matching_types_returned(
    use_case: ListGroupEventsUseCase,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    group_event_repository: FakeGroupEventRepository,
):
    group_id, owner_id = _save_group_with_owner(group_repository, group_member_repository)

    group_event_repository.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="UserAddedToGroupEvent",
        occurred_on=datetime(2026, 2, 6, 10, 0, 0),
        actor_user_id=owner_id,
        event_data={"group_id": str(group_id), "user_id": str(owner_id)},
    )
    group_event_repository.append_event(
        event_id=UUID("b2222222-2222-2222-2222-222222222222"),
        event_type="UserRemovedFromGroupEvent",
        occurred_on=datetime(2026, 2, 6, 11, 0, 0),
        actor_user_id=owner_id,
        event_data={"group_id": str(group_id), "user_id": str(owner_id)},
    )

    response = use_case.execute(
        ListGroupEventsCommand(
            group_id=group_id,
            requesting_user=ADMIN_USER,
            event_types=["UserRemovedFromGroupEvent"],
        )
    )

    assert len(response.events) == 1
    assert response.events[0].event_type == "UserRemovedFromGroupEvent"


def test_given_events_from_another_group_when_listing_group_events_then_they_are_excluded(
    use_case: ListGroupEventsUseCase,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    group_event_repository: FakeGroupEventRepository,
):
    group_id, owner_id = _save_group_with_owner(group_repository, group_member_repository)
    other_group_id = UUID("523e4567-e89b-12d3-a456-426614174004")

    group_event_repository.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="UserAddedToGroupEvent",
        occurred_on=datetime(2026, 2, 6, 10, 0, 0),
        actor_user_id=owner_id,
        event_data={"group_id": str(other_group_id), "user_id": str(owner_id)},
    )

    response = use_case.execute(ListGroupEventsCommand(group_id=group_id, requesting_user=ADMIN_USER))

    assert len(response.events) == 0
