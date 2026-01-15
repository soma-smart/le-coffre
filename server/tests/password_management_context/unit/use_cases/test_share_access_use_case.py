from uuid import UUID, uuid4
import pytest
from password_management_context.application.use_cases import (
    ShareAccessUseCase,
)
from password_management_context.application.commands import ShareResourceCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.domain.value_objects import PasswordPermission
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordNotFoundError,
)


@pytest.fixture()
def use_case(
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
):
    return ShareAccessUseCase(password_repository, password_permissions_repository)


@pytest.fixture()
def password():
    return Password(uuid4(), "toto", "encrypted_value", "default")


def test_given_owner_when_sharing_should_grant_read_access(
    use_case: ShareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
):
    # Arrange: Given an owner of a resource
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    password_permissions_repository.set_owner(owner_id, password_id)

    # Act: When owner shares the resource
    use_case.execute(ShareResourceCommand(owner_id, user_id, password_id))

    # Assert: Then the recipient should have READ access only
    assert password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )


def test_given_non_owner_with_permissions_when_sharing_should_fail(
    use_case: ShareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
):
    # Arrange: Given a user with UPDATE permission but not owner
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    non_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    third_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e8")

    password_repository.save(password)
    password_permissions_repository.set_owner(owner_id, password_id)
    password_permissions_repository.grant_access(
        non_owner_id, password_id, PasswordPermission.READ
    )

    # Act & Assert: When non-owner tries to share, then should fail
    with pytest.raises(PasswordAccessDeniedError):
        use_case.execute(ShareResourceCommand(non_owner_id, third_user_id, password_id))

    # Assert: Third user should not have access
    assert password_permissions_repository.has_access(
        third_user_id, password_id, PasswordPermission.READ
    )


def test_given_owner_when_sharing_already_shared_resource_should_succeed(
    use_case: ShareAccessUseCase,
    password_repository: PasswordRepository,
    password_permissions_repository: PasswordPermissionsRepository,
    password,
):
    # Arrange
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    password_permissions_repository.set_owner(owner_id, password_id)
    password_permissions_repository.grant_access(
        user_id, password_id, PasswordPermission.READ
    )

    # Act
    use_case.execute(ShareResourceCommand(owner_id, user_id, password_id))

    # Assert
    assert password_permissions_repository.has_access(
        user_id, password_id, PasswordPermission.READ
    )


def test_given_non_existing_password_when_sharing_should_fail(
    use_case: ShareAccessUseCase,
):
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(ShareResourceCommand(owner_id, user_id, password_id))
