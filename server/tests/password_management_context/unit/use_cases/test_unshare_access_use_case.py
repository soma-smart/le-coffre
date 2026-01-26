from uuid import UUID, uuid4
import pytest
from password_management_context.application.use_cases import UnshareAccessUseCase
from password_management_context.application.commands import UnshareResourceCommand
from password_management_context.domain.entities.password import Password
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    CannotUnshareWithOwnerError,
    PasswordNotFoundError,
)
from ..fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeGroupAccessGateway,
)
from password_management_context.domain.value_objects import PasswordPermission


@pytest.fixture()
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    return UnshareAccessUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


@pytest.fixture()
def password():
    return Password(uuid4(), "toto", "encrypted_value", "default")


def test_given_owner_when_unsharing_from_user_with_read_access_should_revoke_access(
    use_case: UnshareAccessUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password,
):
    # Arrange: Given an owner and a group with READ access
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    target_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    # Set owner group
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Grant READ to target group
    password_permissions_repository.grant_access(
        target_group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(
        target_group_id, UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    )

    # Act: When owner unshares from the group
    use_case.execute(UnshareResourceCommand(owner_id, target_group_id, password.id))

    # Assert: Then the group should no longer have READ access
    assert not password_permissions_repository.has_access(
        target_group_id, password.id, PasswordPermission.READ
    )


def test_given_non_owner_when_unsharing_should_fail(
    use_case: UnshareAccessUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password,
):
    # Arrange: Given a non-owner trying to unshare
    not_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    target_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    # Grant READ to target group but no owner set
    password_permissions_repository.grant_access(
        target_group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(
        target_group_id, UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    )

    # Act & Assert: When non-owner tries to unshare, should fail
    with pytest.raises(PasswordAccessDeniedError):
        use_case.execute(
            UnshareResourceCommand(not_owner_id, target_group_id, password.id)
        )


def test_given_owner_when_unsharing_from_another_owner_should_fail(
    use_case: UnshareAccessUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password,
):
    # Arrange: Test that we cannot unshare from the owner group
    first_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    first_owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    # In pure group model, there's only one owner group
    # This test tries to unshare from the owner group itself

    password_repository.save(password)
    password_permissions_repository.set_owner(first_owner_group_id, password.id)
    group_access_gateway.set_group_owner(first_owner_group_id, first_owner_id)

    # Act: When owner tries to unshare from the owner group itself
    with pytest.raises(CannotUnshareWithOwnerError):
        use_case.execute(
            UnshareResourceCommand(first_owner_id, first_owner_group_id, password.id)
        )


def test_given_no_password_when_unsharing_should_fail(
    use_case: UnshareAccessUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    # Arrange: Given an owner and a user with READ access
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_permissions_repository.set_owner(owner_id, password_id)
    password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )

    # Act: When owner unshares the resource
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(UnshareResourceCommand(owner_id, user_id, password_id))
