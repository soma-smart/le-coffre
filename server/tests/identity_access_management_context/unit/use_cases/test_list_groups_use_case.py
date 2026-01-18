import pytest
from uuid import uuid4

from identity_access_management_context.application.use_cases import ListGroupsUseCase
from identity_access_management_context.domain.entities import Group


@pytest.fixture
def use_case(group_repository):
    return ListGroupsUseCase(group_repository)


def test_given_no_groups_when_listings_groups_should_return_empty_list(use_case):
    result = use_case.execute()
    assert result == []


def test_given_groups_when_listing_groups_should_return_list_of_groups(
    use_case, group_repository
):
    group1 = uuid4()
    group2 = uuid4()

    group_repository.save_group(
        Group(id=group1, name="Group 1", is_personal=False, user_id=None)
    )
    group_repository.save_group(
        Group(id=group2, name="Group 2", is_personal=False, user_id=None)
    )

    result = use_case.execute()

    assert len(result) == 2
    assert Group(id=group1, name="Group 1", is_personal=False, user_id=None) in result
    assert Group(id=group2, name="Group 2", is_personal=False, user_id=None) in result


def test_given_mixed_groups_when_listing_with_personal_should_return_all(
    use_case, group_repository
):
    personal_group_id = uuid4()
    shared_group_id = uuid4()
    user_id = uuid4()

    group_repository.save_group(
        Group(
            id=personal_group_id,
            name="Personal Group",
            is_personal=True,
            user_id=user_id,
        )
    )
    group_repository.save_group(
        Group(id=shared_group_id, name="Shared Group", is_personal=False, user_id=None)
    )

    result = use_case.execute(include_personal=True)

    assert len(result) == 2
    assert any(g.id == personal_group_id and g.is_personal for g in result)
    assert any(g.id == shared_group_id and not g.is_personal for g in result)


def test_given_mixed_groups_when_listing_without_personal_should_return_only_shared(
    use_case, group_repository
):
    personal_group_id = uuid4()
    shared_group_id = uuid4()
    user_id = uuid4()

    group_repository.save_group(
        Group(
            id=personal_group_id,
            name="Personal Group",
            is_personal=True,
            user_id=user_id,
        )
    )
    group_repository.save_group(
        Group(id=shared_group_id, name="Shared Group", is_personal=False, user_id=None)
    )

    result = use_case.execute(include_personal=False)

    assert len(result) == 1
    assert result[0].id == shared_group_id
    assert not result[0].is_personal
