from uuid import UUID
import pytest

from group_management_context.application.commands import CreateGroupCommand
from group_management_context.application.use_cases import CreateGroupUseCase
from group_management_context.domain.exceptions import (
    GroupNameAlreadyExistsException,
    GroupNameTooShortException,
)
from .fakes import FakeGroupRepository


@pytest.fixture
def group_repository():
    return FakeGroupRepository()


@pytest.fixture
def create_group(group_repository):
    return CreateGroupUseCase(group_repository)


def test_should_create_group_successfully(create_group, group_repository):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_name = "My Test Group"
    group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    command = CreateGroupCommand(user_id=user_id, name=group_name, group_id=group_id)

    result = create_group.execute(command)

    assert result.group_id == group_id
    created_group = group_repository.get_by_id(result.group_id)
    assert created_group is not None
    assert created_group.name == group_name
    assert created_group.owner_id == user_id


def test_should_fail_when_name_is_less_than_10_chars(create_group):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_name = "Short"
    group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    command = CreateGroupCommand(user_id=user_id, name=group_name, group_id=group_id)

    with pytest.raises(GroupNameTooShortException):
        create_group.execute(command)


def test_should_fail_when_group_name_already_exists(create_group):
    user_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_name = "Existing Group"
    group_id_1 = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    group_id_2 = UUID("6d742e0e-bb76-4728-83ef-8d546d7c62e6")
    command_1 = CreateGroupCommand(user_id=user_id, name=group_name, group_id=group_id_1)

    create_group.execute(command_1)

    command_2 = CreateGroupCommand(user_id=user_id, name=group_name, group_id=group_id_2)
    with pytest.raises(GroupNameAlreadyExistsException):
        create_group.execute(command_2)
