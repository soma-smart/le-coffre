import pytest
from uuid import UUID

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
) -> ListAccessUseCase:
    return ListAccessUseCase(password_repository, password_permissions_repository)


@pytest.fixture
def password():
    return Password(
        UUID("12345678-1234-5678-1234-567812345678"),
        "toto",
        "encrypted_value",
        "default",
    )


def test_given_owner_and_password_when_listing_access_should_succeed(
    use_case, password_repository, password_permissions_repository, password
):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")

    password_repository.save(password)
    password_permissions_repository.set_owner(requester_id, password.id)

    response: ListAccessResponse = use_case.execute(
        requester_id=requester_id, password_id=password.id
    )

    assert len(response.accesses) == 1
    assert response.accesses[0].user_id == requester_id
    assert response.accesses[0].is_owner is True


def test_given_user_and_password_when_listing_access_should_succeed(
    use_case, password_repository, password_permissions_repository, password
):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")

    password_repository.save(password)
    password_permissions_repository.grant_access(
        requester_id, password.id, PasswordPermission.READ
    )

    response: ListAccessResponse = use_case.execute(
        requester_id=requester_id, password_id=password.id
    )

    assert len(response.accesses) == 1
    assert response.accesses[0].user_id == requester_id
    assert response.accesses[0].is_owner is False
    assert PasswordPermission.READ in response.accesses[0].permissions


def test_given_no_password_when_listing_access_should_fail(use_case):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(
            requester_id=requester_id,
            password_id=UUID("12345678-1234-5678-1234-567812345678"),
        )


def test_given_multiple_user_having_access_when_listing_access_should_have_them_all(
    use_case, password_repository, password_permissions_repository, password
):
    requester_id = UUID("87654321-4321-8765-4321-876543218765")
    user1_id = UUID("22345678-1234-5678-1234-567812345678")
    user2_id = UUID("32345678-1234-5678-1234-567812345678")

    password_repository.save(password)
    password_permissions_repository.set_owner(requester_id, password.id)
    password_permissions_repository.grant_access(
        user1_id, password.id, PasswordPermission.READ
    )
    password_permissions_repository.grant_access(
        user2_id, password.id, PasswordPermission.READ
    )

    response: ListAccessResponse = use_case.execute(
        requester_id=requester_id, password_id=password.id
    )

    assert len(response.accesses) == 3
    for user in response.accesses:
        if user.user_id == requester_id:
            assert user.is_owner is True
        else:
            assert PasswordPermission.READ in user.permissions
        assert user.user_id in {requester_id, user1_id, user2_id}
