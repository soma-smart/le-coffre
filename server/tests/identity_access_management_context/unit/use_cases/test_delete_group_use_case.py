import pytest
from uuid import UUID

from identity_access_management_context.application.gateways import (
    GroupRepository,
    GroupMemberRepository,
    GroupUsageGateway,
)
from identity_access_management_context.application.commands import DeleteGroupCommand
from identity_access_management_context.application.use_cases import DeleteGroupUseCase
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    UserNotOwnerOfGroupException,
    CannotDeletePersonalGroupException,
    CannotDeleteGroupStillUsedException,
)
from identity_access_management_context.domain.entities import Group
from shared_kernel.authentication import AuthenticatedUser
from shared_kernel.authentication.constants import ADMIN_ROLE


@pytest.fixture
def use_case(
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
    group_usage_gateway: GroupUsageGateway,
):
    return DeleteGroupUseCase(
        group_repository=group_repository,
        group_member_repository=group_member_repository,
        group_usage_gateway=group_usage_gateway,
    )


def test_given_owner_and_group_without_passwords_when_deleting_group_then_group_is_deleted(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    requesting_user = AuthenticatedUser(user_id=owner_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act
    use_case.execute(command)

    # Assert
    assert group_repository.get_by_id(group_id) is None


def test_given_non_owner_user_when_deleting_group_then_raises_user_not_owner_exception(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    non_owner_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    group_member_repository.add_member(group_id, non_owner_id, is_owner=False)

    requesting_user = AuthenticatedUser(user_id=non_owner_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act & Assert
    with pytest.raises(UserNotOwnerOfGroupException):
        use_case.execute(command)


def test_given_non_existent_group_when_deleting_group_then_raises_group_not_found_exception(
    use_case: DeleteGroupUseCase,
):
    # Arrange
    requester_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    non_existent_group_id = UUID("999e4567-e89b-12d3-a456-426614174999")

    requesting_user = AuthenticatedUser(user_id=requester_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=non_existent_group_id,
    )

    # Act & Assert
    with pytest.raises(GroupNotFoundException):
        use_case.execute(command)


def test_given_personal_group_when_deleting_group_then_raises_cannot_delete_personal_group_exception(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    personal_group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    personal_group = Group(
        id=personal_group_id,
        name="Personal Group",
        is_personal=True,
        user_id=user_id,
    )
    group_repository.save_group(personal_group)
    group_member_repository.add_member(personal_group_id, user_id, is_owner=True)

    requesting_user = AuthenticatedUser(user_id=user_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=personal_group_id,
    )

    # Act & Assert
    with pytest.raises(CannotDeletePersonalGroupException):
        use_case.execute(command)


def test_given_group_with_passwords_when_deleting_group_then_raises_cannot_delete_group_with_passwords_exception(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
    group_usage_gateway: GroupUsageGateway,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)

    # Simulate that this group owns passwords
    group_usage_gateway._set_usage_to_group(group_id)

    requesting_user = AuthenticatedUser(user_id=owner_id, roles=[])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act & Assert
    with pytest.raises(CannotDeleteGroupStillUsedException):
        use_case.execute(command)


def test_given_admin_user_not_owner_when_deleting_group_then_group_is_deleted(
    use_case: DeleteGroupUseCase,
    group_repository: GroupRepository,
    group_member_repository: GroupMemberRepository,
):
    # Arrange
    owner_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    admin_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    group_id = UUID("323e4567-e89b-12d3-a456-426614174002")

    group = Group(
        id=group_id,
        name="Test Group",
        is_personal=False,
    )
    group_repository.save_group(group)
    group_member_repository.add_member(group_id, owner_id, is_owner=True)
    # Admin is not a member of the group

    requesting_user = AuthenticatedUser(user_id=admin_id, roles=[ADMIN_ROLE])
    command = DeleteGroupCommand(
        requesting_user=requesting_user,
        group_id=group_id,
    )

    # Act
    use_case.execute(command)

    # Assert
    assert group_repository.get_by_id(group_id) is None
