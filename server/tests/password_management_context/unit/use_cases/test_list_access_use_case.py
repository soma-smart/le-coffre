import pytest
from uuid import UUID

from password_management_context.application.responses.list_access_response import (
    UserAccessResponse,
    GroupAccessResponse,
)
from password_management_context.application.use_cases import ListAccessUseCase
from password_management_context.application.responses import ListAccessResponse
from password_management_context.domain.entities import Password
from password_management_context.domain.value_objects import PasswordPermission
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.domain.exceptions import PasswordNotFoundError


@pytest.fixture
def use_case(
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    group_access_gateway,
) -> ListAccessUseCase:
    return ListAccessUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


@pytest.fixture
def password():
    return Password(
        UUID("12345678-1234-5678-1234-567812345678"),
        "toto",
        "encrypted_value",
        "default",
    )


def test_given_owner_and_password_when_listing_access_should_succeed(
    use_case,
    password_repository,
    password_permissions_repository,
    password,
    group_access_gateway,
):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")
    group_id = UUID("97654321-4321-8765-4321-876543218765")

    password_repository.save(password)
    # Set group as owner and user as owner of group
    password_permissions_repository.set_owner(group_id, password.id)
    group_access_gateway.set_group_owner(group_id, requester_id)

    response: ListAccessResponse = use_case.execute(
        requester_id=requester_id, password_id=password.id
    )

    assert len(response.user_accesses) == 1
    assert response.user_accesses[0].user_id == requester_id
    assert response.user_accesses[0].is_owner is True

    assert len(response.group_accesses) == 1
    assert response.group_accesses[0].group_id == group_id
    assert response.group_accesses[0].is_owner is True


def test_given_user_and_password_when_listing_access_should_succeed(
    use_case,
    password_repository,
    password_permissions_repository,
    password,
    group_access_gateway,
):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")
    group_id = UUID("97654321-4321-8765-4321-876543218765")

    password_repository.save(password)
    # Grant READ permission to group and set user as owner of group
    password_permissions_repository.grant_access(
        group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(group_id, requester_id)

    response: ListAccessResponse = use_case.execute(
        requester_id=requester_id, password_id=password.id
    )

    assert len(response.user_accesses) == 1
    assert response.user_accesses[0].user_id == requester_id
    assert response.user_accesses[0].is_owner is False
    assert PasswordPermission.READ in response.user_accesses[0].permissions

    assert len(response.group_accesses) == 1
    assert response.group_accesses[0].group_id == group_id
    assert response.group_accesses[0].is_owner is False


def test_given_no_password_when_listing_access_should_fail(use_case):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(
            requester_id=requester_id,
            password_id=UUID("12345678-1234-5678-1234-567812345678"),
        )


def test_given_multiple_user_having_access_when_listing_access_should_have_them_all(
    use_case,
    password_repository,
    password_permissions_repository,
    password,
    group_access_gateway,
):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")
    owner_group_id = UUID("97654321-4321-8765-4321-876543218765")
    group1_id = UUID("22345678-1234-5678-1234-567812345678")
    group2_id = UUID("32345678-1234-5678-1234-567812345678")
    user1_id = UUID("11111111-1111-1111-1111-111111111111")
    user2_id = UUID("22222222-2222-2222-2222-222222222222")

    password_repository.save(password)
    # Set owner group and user as owner of it
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, requester_id)
    # Grant access to other groups with users
    password_permissions_repository.grant_access(
        group1_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(group1_id, user1_id)
    password_permissions_repository.grant_access(
        group2_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(group2_id, user2_id)

    response: ListAccessResponse = use_case.execute(
        requester_id=requester_id, password_id=password.id
    )

    assert len(response.user_accesses) == 3
    user_ids = {access.user_id for access in response.user_accesses}
    assert user_ids == {requester_id, user1_id, user2_id}

    for access in response.user_accesses:
        if access.user_id == requester_id:
            assert access.is_owner is True
        else:
            assert PasswordPermission.READ in access.permissions

    assert len(response.group_accesses) == 3
    group_ids = {access.group_id for access in response.group_accesses}
    assert group_ids == {owner_group_id, group1_id, group2_id}

    for access in response.group_accesses:
        if access.group_id == owner_group_id:
            assert access.is_owner is True
        else:
            assert access.is_owner is False


def test_given_owner_from_one_group_and_member_for_other_when_listing_access_should_have_them_all(
    use_case,
    password_repository,
    password_permissions_repository,
    password,
    group_access_gateway,
):
    owner_id = UUID("11111111-1111-1111-1111-111111111111")
    member_id = UUID("22222222-2222-2222-2222-222222222222")
    owner_group_id = UUID("97654321-4321-8765-4321-876543218765")
    member_group_id = UUID("87654321-4321-8765-4321-876543218765")

    password_repository.save(password)
    # Set owner group and user as owner of it
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Grant access to member group
    password_permissions_repository.grant_access(
        member_group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(member_group_id, owner_id)
    group_access_gateway.add_group_member(member_group_id, member_id)

    response: ListAccessResponse = use_case.execute(
        requester_id=owner_id, password_id=password.id
    )

    assert len(response.user_accesses) == 2

    assert UserAccessResponse(owner_id, set([]), True) in response.user_accesses
    assert (
        UserAccessResponse(member_id, set([PasswordPermission.READ]), False)
        in response.user_accesses
    )

    assert len(response.group_accesses) == 2

    assert GroupAccessResponse(owner_group_id, set([]), True) in response.group_accesses
    assert (
        GroupAccessResponse(member_group_id, set([PasswordPermission.READ]), False)
        in response.group_accesses
    )
