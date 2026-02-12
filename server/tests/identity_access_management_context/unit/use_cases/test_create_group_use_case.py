import pytest
from uuid import UUID


from identity_access_management_context.application.commands import CreateGroupCommand
from identity_access_management_context.application.use_cases import CreateGroupUseCase
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
)
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.events import GroupCreatedEvent
from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from ..fakes import (
    FakeUserRepository,
    FakeGroupRepository,
    FakeGroupMemberRepository,
)


@pytest.fixture
def use_case(
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
    event_publisher,
    iam_event_repository,
):
    return CreateGroupUseCase(
        user_repository=user_repository,
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        event_publisher=event_publisher,
        iam_event_repository=iam_event_repository,
    )


def test_given_valid_data_when_creating_group_then_group_is_created(
    use_case: CreateGroupUseCase,
    user_repository: FakeUserRepository,
    group_repository: FakeGroupRepository,
):
    group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    creator_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_name = "Development Team"

    user = User(
        id=creator_id,
        username="creator",
        email="creator@example.com",
        name="Creator User",
    )
    user_repository.save(user)

    command = CreateGroupCommand(
        id=group_id,
        name=group_name,
        creator_id=creator_id,
    )

    result_id = use_case.execute(command)

    assert result_id == group_id
    created_group = group_repository.get_by_id(group_id)
    assert created_group is not None
    assert created_group.id == group_id
    assert created_group.name == group_name
    assert created_group.is_personal is False


def test_given_valid_data_when_creating_group_then_creator_is_added_as_owner(
    use_case: CreateGroupUseCase,
    user_repository: FakeUserRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    creator_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_name = "Development Team"

    user = User(
        id=creator_id,
        username="creator",
        email="creator@example.com",
        name="Creator User",
    )
    user_repository.save(user)

    command = CreateGroupCommand(
        id=group_id,
        name=group_name,
        creator_id=creator_id,
    )

    use_case.execute(command)

    assert group_member_repository.is_owner(group_id, creator_id)
    assert group_member_repository.is_member(group_id, creator_id)


def test_given_user_not_found_when_creating_group_then_raise_user_not_found_exception(
    use_case: CreateGroupUseCase,
):
    group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    nonexistent_creator_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    command = CreateGroupCommand(
        id=group_id,
        name="Development Team",
        creator_id=nonexistent_creator_id,
    )

    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_valid_data_when_creating_group_then_should_publish_group_created_event(
    use_case: CreateGroupUseCase,
    user_repository: FakeUserRepository,
    event_publisher: FakeDomainEventPublisher,
):
    group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    creator_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    user = User(id=creator_id, username="creator", email="creator@example.com", name="Creator User")
    user_repository.save(user)

    command = CreateGroupCommand(id=group_id, name="Development Team", creator_id=creator_id)
    use_case.execute(command)

    events = event_publisher.get_published_events_of_type(GroupCreatedEvent)
    assert len(events) == 1
    assert events[0].group_id == group_id
    assert events[0].group_name == "Development Team"
    assert events[0].created_by_user_id == creator_id
