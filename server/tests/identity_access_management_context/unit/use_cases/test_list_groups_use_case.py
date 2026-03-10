from uuid import uuid4

import pytest

from identity_access_management_context.application.commands import ListGroupsCommand
from identity_access_management_context.application.use_cases import ListGroupsUseCase
from identity_access_management_context.domain.entities import Group

from ..fakes import FakeGroupMemberRepository, FakeGroupRepository


@pytest.fixture
def use_case(
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    return ListGroupsUseCase(group_repository, group_member_repository)


def test_given_no_groups_when_listings_groups_should_return_empty_list(use_case):
    command = ListGroupsCommand()
    result = use_case.execute(command)
    assert result.groups == []


def test_given_groups_when_listing_groups_should_return_list_of_groups(
    use_case,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    group1 = uuid4()
    group2 = uuid4()
    user1 = uuid4()
    user2 = uuid4()

    group_repository.save_group(Group(id=group1, name="Group 1", is_personal=False, user_id=None))
    group_repository.save_group(Group(id=group2, name="Group 2", is_personal=False, user_id=None))

    # Add owners to the groups
    group_member_repository.add_member(group1, user1, is_owner=True)
    group_member_repository.add_member(group2, user2, is_owner=True)

    command = ListGroupsCommand()
    result = use_case.execute(command)

    assert len(result.groups) == 2
    assert result.groups[0].id == group1
    assert result.groups[0].name == "Group 1"
    assert result.groups[0].is_personal is False
    assert result.groups[0].user_id is None
    assert result.groups[0].owners == [user1]

    assert result.groups[1].id == group2
    assert result.groups[1].name == "Group 2"
    assert result.groups[1].is_personal is False
    assert result.groups[1].user_id is None
    assert result.groups[1].owners == [user2]


def test_given_mixed_groups_when_listing_with_personal_should_return_all(
    use_case,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    personal_group_id = uuid4()
    shared_group_id = uuid4()
    user_id = uuid4()
    owner_id = uuid4()

    group_repository.save_group(
        Group(
            id=personal_group_id,
            name="Personal Group",
            is_personal=True,
            user_id=user_id,
        )
    )
    group_repository.save_group(Group(id=shared_group_id, name="Shared Group", is_personal=False, user_id=None))

    # Add owner to shared group
    group_member_repository.add_member(shared_group_id, owner_id, is_owner=True)

    command = ListGroupsCommand(include_personal=True)
    result = use_case.execute(command)

    assert len(result.groups) == 2

    # Check personal group
    personal_group = next(g for g in result.groups if g.id == personal_group_id)
    assert personal_group.is_personal is True
    assert personal_group.user_id == user_id
    assert personal_group.owners == [user_id]  # Personal group owner is user_id

    # Check shared group
    shared_group = next(g for g in result.groups if g.id == shared_group_id)
    assert shared_group.is_personal is False
    assert shared_group.user_id is None
    assert shared_group.owners == [owner_id]


def test_given_mixed_groups_when_listing_without_personal_should_return_only_shared(
    use_case,
    group_repository: FakeGroupRepository,
    group_member_repository: FakeGroupMemberRepository,
):
    personal_group_id = uuid4()
    shared_group_id = uuid4()
    user_id = uuid4()
    owner_id = uuid4()

    group_repository.save_group(
        Group(
            id=personal_group_id,
            name="Personal Group",
            is_personal=True,
            user_id=user_id,
        )
    )
    group_repository.save_group(Group(id=shared_group_id, name="Shared Group", is_personal=False, user_id=None))

    # Add owner to shared group
    group_member_repository.add_member(shared_group_id, owner_id, is_owner=True)

    command = ListGroupsCommand(include_personal=False)
    result = use_case.execute(command)

    assert len(result.groups) == 1
    assert result.groups[0].id == shared_group_id
    assert result.groups[0].is_personal is False
    assert result.groups[0].owners == [owner_id]
