import pytest
from uuid import UUID

from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.application.commands import (
    AddOwnerToGroupCommand,
)
from identity_access_management_context.application.use_cases import (
    AddOwnerToGroupUseCase,
)
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotModifyPersonalGroupException,
    UserNotMemberOfGroupException,
)
from identity_access_management_context.domain.entities import User, Group


@pytest.fixture
def use_case(
    user_repository: UserRepository,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    return AddOwnerToGroupUseCase(
        user_repository=user_repository,
        group_repository=group_repository,
        group_member_repository=group_member_repository,
    )


def test_given_owner_when_adding_existing_member_as_owner_then_member_becomes_owner(
    use_case: AddOwnerToGroupUseCase,
    user_repository: UserRepository,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    member_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    member = User(
        id=member_id,
        username="member",
        email="member@example.com",
        name="Member User",
    )
    user_repository.save(owner)
    user_repository.save(member)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, member_id, is_owner=False)

    command = AddOwnerToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=member_id,
    )

    use_case.execute(command)

    assert group_member_repository.is_owner(group_id, member_id)


def test_given_non_owner_when_adding_owner_to_group_then_raise_user_not_owner_exception(
    use_case: AddOwnerToGroupUseCase,
    user_repository: UserRepository,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    non_owner_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    member_id = UUID("423e4567-e89b-12d3-a456-426614174003")

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
    member = User(
        id=member_id,
        username="member",
        email="member@example.com",
        name="Member User",
    )
    user_repository.save(owner)
    user_repository.save(non_owner)
    user_repository.save(member)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, member_id, is_owner=False)

    command = AddOwnerToGroupCommand(
        requester_id=non_owner_id,
        group_id=group_id,
        user_id=member_id,
    )

    with pytest.raises(UserNotOwnerOfGroupException):
        use_case.execute(command)


def test_given_group_not_found_when_adding_owner_then_raise_group_not_found_exception(
    use_case: AddOwnerToGroupUseCase,
    user_repository: UserRepository,
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

    command = AddOwnerToGroupCommand(
        requester_id=requester_id,
        group_id=nonexistent_group_id,
        user_id=user_id,
    )

    with pytest.raises(GroupNotFoundException):
        use_case.execute(command)


def test_given_personal_group_when_adding_owner_then_raise_cannot_modify_personal_group_exception(
    use_case: AddOwnerToGroupUseCase,
    user_repository: UserRepository,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    member_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    member = User(
        id=member_id,
        username="member",
        email="member@example.com",
        name="Member User",
    )
    user_repository.save(owner)
    user_repository.save(member)

    group = Group(
        id=group_id, name="Personal Group", is_personal=True, user_id=owner_id
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    command = AddOwnerToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=member_id,
    )

    with pytest.raises(CannotModifyPersonalGroupException):
        use_case.execute(command)


def test_given_user_not_found_when_adding_owner_then_raise_user_not_found_exception(
    use_case: AddOwnerToGroupUseCase,
    user_repository: UserRepository,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
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

    command = AddOwnerToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=nonexistent_user_id,
    )

    with pytest.raises(UserNotFoundException):
        use_case.execute(command)


def test_given_user_not_member_when_adding_as_owner_then_raise_user_not_member_exception(
    use_case: AddOwnerToGroupUseCase,
    user_repository: UserRepository,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    non_member_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
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

    command = AddOwnerToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=non_member_id,
    )

    with pytest.raises(UserNotMemberOfGroupException):
        use_case.execute(command)


def test_given_user_already_owner_when_adding_as_owner_then_operation_is_idempotent(
    use_case: AddOwnerToGroupUseCase,
    user_repository: UserRepository,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    existing_owner_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    owner = User(
        id=owner_id,
        username="owner",
        email="owner@example.com",
        name="Owner User",
    )
    existing_owner = User(
        id=existing_owner_id,
        username="existingowner",
        email="existingowner@example.com",
        name="Existing Owner User",
    )
    user_repository.save(owner)
    user_repository.save(existing_owner)

    group = Group(id=group_id, name="Development Team", is_personal=False)
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, existing_owner_id, is_owner=True)

    command = AddOwnerToGroupCommand(
        requester_id=owner_id,
        group_id=group_id,
        user_id=existing_owner_id,
    )

    use_case.execute(command)

    assert group_member_repository.is_owner(group_id, existing_owner_id)
