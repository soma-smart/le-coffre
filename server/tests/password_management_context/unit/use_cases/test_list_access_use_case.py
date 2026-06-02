from uuid import UUID

import pytest

from password_management_context.application.commands import ListAccessCommand
from password_management_context.application.responses import ListAccessResponse
from password_management_context.application.use_cases import ListAccessUseCase
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordNotFoundError,
)
from password_management_context.domain.value_objects import AccessRole, PasswordPermission

from ..fakes import (
    FakeGroupAccessGateway,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
)

OWNER_GROUP_ID = UUID("97654321-4321-8765-4321-876543218765")
SHARED_GROUP_ID = UUID("22345678-1234-5678-1234-567812345678")
OWNER_USER_ID = UUID("11111111-1111-1111-1111-111111111111")
MEMBER_USER_ID = UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
) -> ListAccessUseCase:
    return ListAccessUseCase(password_repository, password_permissions_repository, group_access_gateway)


@pytest.fixture
def password(password_repository: FakePasswordRepository) -> Password:
    pwd = Password(
        UUID("12345678-1234-5678-1234-567812345678"),
        "toto",
        "encrypted_value",
        "default",
    )
    password_repository.save(pwd)
    return pwd


def _user_link(response: ListAccessResponse, user_id: UUID, group_id: UUID):
    matches = [link for link in response.user_accesses if link.user_id == user_id and link.group_id == group_id]
    assert len(matches) == 1, f"expected exactly one link for {user_id} via {group_id}, got {matches}"
    return matches[0]


def test_given_owner_of_owner_group_when_listing_access_should_return_owner_owner_link(
    use_case: ListAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password: Password,
):
    password_permissions_repository.set_owner(OWNER_GROUP_ID, password.id)
    group_access_gateway.set_group_owner(OWNER_GROUP_ID, OWNER_USER_ID)

    response = use_case.execute(ListAccessCommand(requester_id=OWNER_USER_ID, password_id=password.id))

    link = _user_link(response, OWNER_USER_ID, OWNER_GROUP_ID)
    assert link.role_in_group is AccessRole.OWNER
    assert link.group_role is AccessRole.OWNER


def test_given_member_of_shared_group_when_listing_access_should_return_member_member_link(
    use_case: ListAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password: Password,
):
    # Owner group so the password exists with an owner; requester is the owner.
    password_permissions_repository.set_owner(OWNER_GROUP_ID, password.id)
    group_access_gateway.set_group_owner(OWNER_GROUP_ID, OWNER_USER_ID)
    # Shared group with a plain member — this is the user that used to vanish.
    password_permissions_repository.grant_access(SHARED_GROUP_ID, password.id, PasswordPermission.READ)
    group_access_gateway.set_group_owner(SHARED_GROUP_ID, OWNER_USER_ID)
    group_access_gateway.add_group_member(SHARED_GROUP_ID, MEMBER_USER_ID)

    response = use_case.execute(ListAccessCommand(requester_id=OWNER_USER_ID, password_id=password.id))

    link = _user_link(response, MEMBER_USER_ID, SHARED_GROUP_ID)
    assert link.role_in_group is AccessRole.MEMBER
    assert link.group_role is AccessRole.MEMBER
    assert PasswordPermission.READ in link.permissions


def test_given_owner_of_shared_group_when_listing_access_should_return_owner_member_link(
    use_case: ListAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password: Password,
):
    password_permissions_repository.grant_access(SHARED_GROUP_ID, password.id, PasswordPermission.READ)
    group_access_gateway.set_group_owner(SHARED_GROUP_ID, OWNER_USER_ID)

    response = use_case.execute(ListAccessCommand(requester_id=OWNER_USER_ID, password_id=password.id))

    link = _user_link(response, OWNER_USER_ID, SHARED_GROUP_ID)
    assert link.role_in_group is AccessRole.OWNER
    assert link.group_role is AccessRole.MEMBER


def test_given_member_of_owner_group_when_listing_access_should_return_member_owner_link(
    use_case: ListAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password: Password,
):
    password_permissions_repository.set_owner(OWNER_GROUP_ID, password.id)
    group_access_gateway.set_group_owner(OWNER_GROUP_ID, OWNER_USER_ID)
    group_access_gateway.add_group_member(OWNER_GROUP_ID, MEMBER_USER_ID)

    response = use_case.execute(ListAccessCommand(requester_id=MEMBER_USER_ID, password_id=password.id))

    link = _user_link(response, MEMBER_USER_ID, OWNER_GROUP_ID)
    assert link.role_in_group is AccessRole.MEMBER
    assert link.group_role is AccessRole.OWNER


def test_given_user_in_two_groups_when_listing_access_should_return_one_link_per_group(
    use_case: ListAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password: Password,
):
    password_permissions_repository.set_owner(OWNER_GROUP_ID, password.id)
    group_access_gateway.set_group_owner(OWNER_GROUP_ID, OWNER_USER_ID)
    password_permissions_repository.grant_access(SHARED_GROUP_ID, password.id, PasswordPermission.READ)
    group_access_gateway.add_group_member(SHARED_GROUP_ID, OWNER_USER_ID)

    response = use_case.execute(ListAccessCommand(requester_id=OWNER_USER_ID, password_id=password.id))

    via_owner = _user_link(response, OWNER_USER_ID, OWNER_GROUP_ID)
    via_shared = _user_link(response, OWNER_USER_ID, SHARED_GROUP_ID)
    assert via_owner.role_in_group is AccessRole.OWNER
    assert via_owner.group_role is AccessRole.OWNER
    assert via_shared.role_in_group is AccessRole.MEMBER
    assert via_shared.group_role is AccessRole.MEMBER


def test_given_multiple_groups_when_listing_access_should_label_each_group_role(
    use_case: ListAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password: Password,
):
    password_permissions_repository.set_owner(OWNER_GROUP_ID, password.id)
    group_access_gateway.set_group_owner(OWNER_GROUP_ID, OWNER_USER_ID)
    password_permissions_repository.grant_access(SHARED_GROUP_ID, password.id, PasswordPermission.READ)
    group_access_gateway.set_group_owner(SHARED_GROUP_ID, MEMBER_USER_ID)

    response = use_case.execute(ListAccessCommand(requester_id=OWNER_USER_ID, password_id=password.id))

    roles = {g.group_id: g.role for g in response.group_accesses}
    assert roles == {OWNER_GROUP_ID: AccessRole.OWNER, SHARED_GROUP_ID: AccessRole.MEMBER}


def test_given_password_not_exists_when_listing_access_should_raise_password_not_found_error(
    use_case: ListAccessUseCase,
):
    command = ListAccessCommand(
        requester_id=OWNER_USER_ID,
        password_id=UUID("12345678-1234-5678-1234-567812345678"),
    )
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(command)


def test_given_requester_without_access_when_listing_access_should_raise_access_denied_error(
    use_case: ListAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password: Password,
):
    password_permissions_repository.set_owner(OWNER_GROUP_ID, password.id)
    group_access_gateway.set_group_owner(OWNER_GROUP_ID, OWNER_USER_ID)

    outsider = UUID("99999999-9999-9999-9999-999999999999")
    with pytest.raises(PasswordAccessDeniedError):
        use_case.execute(ListAccessCommand(requester_id=outsider, password_id=password.id))
