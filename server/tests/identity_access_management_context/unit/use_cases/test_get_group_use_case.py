import pytest
from uuid import UUID

from identity_access_management_context.application.commands import GetGroupCommand
from identity_access_management_context.application.use_cases import GetGroupUseCase
from identity_access_management_context.application.responses import GetGroupResponse
from identity_access_management_context.domain.entities import Group
from identity_access_management_context.domain.exceptions import GroupNotFoundException


@pytest.fixture
def use_case(group_repository, group_member_repository):
    return GetGroupUseCase(group_repository, group_member_repository)


def test_given_group_when_executed_then_should_return_group(use_case):
    group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group = Group(id=group_id, name="Test Group", is_personal=False)
    use_case.group_repository.get_by_id = lambda x: group if x == group_id else None

    command = GetGroupCommand(group_id=group_id)
    result = use_case.execute(command)

    assert isinstance(result, GetGroupResponse)
    assert result.group == group
    assert result.members == []


def test_given_no_group_when_executed_then_should_raise_group_not_found_exception(
    use_case,
):
    group_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    use_case.group_repository.get_by_id = lambda x: None

    command = GetGroupCommand(group_id=group_id)
    with pytest.raises(GroupNotFoundException):
        use_case.execute(command)
