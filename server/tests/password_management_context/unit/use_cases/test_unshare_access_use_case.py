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
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects import PasswordPermission


@pytest.fixture()
def use_case(
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    return UnshareAccessUseCase(password_repository, password_permissions_repository)


@pytest.fixture()
def password():
    return Password(uuid4(), "toto", "encrypted_value", "default")


def test_given_owner_when_unsharing_from_user_with_read_access_should_revoke_access(
    use_case: UnshareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
):
    # Arrange: Given an owner and a user with READ access
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    password_permissions_repository.set_owner(owner_id, resource_id)
    password_permissions_repository.grant_access(
        user_id, resource_id, PasswordPermission.READ
    )

    # Act: When owner unshares the resource
    use_case.execute(UnshareResourceCommand(owner_id, user_id, resource_id))

    # Assert: Then the user should no longer have READ access
    assert not password_permissions_repository.has_access(
        user_id, resource_id, PasswordPermission.READ
    )


def test_given_non_owner_when_unsharing_should_fail(
    use_case: UnshareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
):
    # Arrange: Given an owner and a user with READ access
    not_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    password_permissions_repository.grant_access(
        user_id, resource_id, PasswordPermission.READ
    )

    # Act: When owner unshares the resource
    with pytest.raises(PasswordAccessDeniedError):
        use_case.execute(UnshareResourceCommand(not_owner_id, user_id, resource_id))


def test_given_owner_when_unsharing_from_another_owner_should_fail(
    use_case: UnshareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
):
    # Arrange: Given an owner and a user with READ access
    first_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    second_owner_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e6")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    password_permissions_repository.set_owner(first_owner_id, resource_id)
    password_permissions_repository.set_owner(second_owner_id, resource_id)
    password_permissions_repository.grant_access(
        user_id, resource_id, PasswordPermission.READ
    )

    # Act: When owner unshares the resource
    with pytest.raises(CannotUnshareWithOwnerError):
        use_case.execute(
            UnshareResourceCommand(first_owner_id, second_owner_id, resource_id)
        )


def test_given_no_password_when_unsharing_should_fail(
    use_case: UnshareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    # Arrange: Given an owner and a user with READ access
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_permissions_repository.set_owner(owner_id, resource_id)
    password_permissions_repository.grant_access(
        user_id, resource_id, PasswordPermission.READ
    )

    # Act: When owner unshares the resource
    with pytest.raises(PasswordNotFoundError):
        use_case.execute(UnshareResourceCommand(owner_id, user_id, resource_id))
