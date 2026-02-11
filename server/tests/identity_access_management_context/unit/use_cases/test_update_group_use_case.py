import pytest
from uuid import UUID

from identity_access_management_context.application.use_cases import (
    UpdateGroupUseCase,
)
from identity_access_management_context.application.commands import (
    UpdateGroupCommand,
)
from identity_access_management_context.application.gateways import (
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
)

from identity_access_management_context.domain.entities import Group

from shared_kernel.domain.entities import AuthenticatedUser
from shared_kernel.domain.value_objects import ADMIN_ROLE


@pytest.fixture
def use_case(
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
    event_publisher,
):
    return UpdateGroupUseCase(
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        event_publisher=event_publisher,
    )


def test_given_user_is_owner_when_updating_group_should_update_group_name(
    use_case: UpdateGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")

    group = Group(
        id=group_id,
        name="Old Name",
        is_personal=False,
        user_id=None,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, requester_id, is_owner=True)

    command = UpdateGroupCommand(
        requesting_user=AuthenticatedUser(requester_id, []),
        group_id=group_id,
        name="New Name",
    )

    use_case.execute(command)

    updated_group = group_repository.get_by_id(group_id)
    assert updated_group is not None
    assert updated_group.name == "New Name"


def test_given_user_is_admin_when_updating_group_should_update_group_name(
    use_case: UpdateGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")

    group = Group(
        id=group_id,
        name="Old Name",
        is_personal=False,
        user_id=None,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, requester_id, is_owner=True)

    command = UpdateGroupCommand(
        requesting_user=AuthenticatedUser(requester_id, [ADMIN_ROLE]),
        group_id=group_id,
        name="New Name",
    )

    use_case.execute(command)

    updated_group = group_repository.get_by_id(group_id)
    assert updated_group is not None
    assert updated_group.name == "New Name"


def test_given_group_not_exists_when_updating_group_should_raise_group_not_found(
    use_case: UpdateGroupUseCase,
):
    non_existent_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")

    command = UpdateGroupCommand(
        requesting_user=AuthenticatedUser(requester_id, []),
        group_id=non_existent_group_id,
        name="New Name",
    )

    with pytest.raises(GroupNotFoundException):
        use_case.execute(command)


def test_given_user_not_owner_nor_admin_when_updating_group_should_raise_user_not_owner(
    use_case: UpdateGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")
    non_owner_id = UUID("2d742e0e-bb76-4728-83ef-8d546d7c62e7")

    group = Group(
        id=group_id,
        name="Old Name",
        is_personal=False,
        user_id=None,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, non_owner_id, is_owner=False)

    command = UpdateGroupCommand(
        requesting_user=AuthenticatedUser(non_owner_id, []),
        group_id=group_id,
        name="New Name",
    )

    with pytest.raises(UserNotOwnerOfGroupException):
        use_case.execute(command)


def test_given_personal_group_when_updating_group_should_raise_cannot_modify_personal_group(
    use_case: UpdateGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    requester_id = UUID("1d742e0e-bb76-4728-83ef-8d546d7c62e6")

    personal_group = Group(
        id=group_id,
        name="Personal Group",
        is_personal=True,
        user_id=requester_id,
    )
    group_repository.save_group(personal_group)
    group_member_repository.add_member(group_id, requester_id, is_owner=True)

    command = UpdateGroupCommand(
        requesting_user=AuthenticatedUser(requester_id, []),
        group_id=group_id,
        name="New Name",
    )

    with pytest.raises(CannotModifyPersonalGroupException):
        use_case.execute(command)
