from uuid import UUID, uuid4
import pytest
from password_management_context.application.use_cases import (
    ShareAccessUseCase,
)
from password_management_context.application.commands import ShareResourceCommand

from ..fakes import (
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeGroupAccessGateway,
)
from password_management_context.domain.value_objects import PasswordPermission
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
)


@pytest.fixture()
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
):
    return ShareAccessUseCase(
        password_repository, password_permissions_repository, group_access_gateway
    )


@pytest.fixture()
def password():
    return Password(uuid4(), "toto", "encrypted_value", "default")


def test_given_owner_and_target_group_when_sharing_access_should_grant_read_permission(
    use_case: ShareAccessUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password,
):
    # Arrange: Given an owner of a resource
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    target_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    # Set owner group and user as owner of it
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Register target group
    group_access_gateway.set_group_owner(
        target_group_id, UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    )

    # Act: When owner shares the resource with a group
    use_case.execute(ShareResourceCommand(owner_id, target_group_id, password.id))

    # Assert: Then the target group should have READ access only
    assert password_permissions_repository.has_access(
        target_group_id, password.id, PasswordPermission.READ
    )


def test_given_non_owner_user_when_sharing_access_should_raise_user_not_owner_error(
    use_case: ShareAccessUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password,
):
    # Arrange: Given a user with READ permission but not owner
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    non_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    non_owner_group_id = UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    third_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e8")

    password_repository.save(password)
    # Set owner group
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Grant READ to non-owner group
    password_permissions_repository.grant_access(
        non_owner_group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(non_owner_group_id, non_owner_id)
    # Register third group
    group_access_gateway.set_group_owner(
        third_group_id, UUID("ad742e0e-bb76-4728-83ef-8d546d7c62e8")
    )

    # Act & Assert: When non-owner tries to share, then should fail
    with pytest.raises(UserNotOwnerOfGroupError):
        use_case.execute(
            ShareResourceCommand(non_owner_id, third_group_id, password.id)
        )

    # Assert: Third group should not have access
    assert not password_permissions_repository.has_access(
        third_group_id, password.id, PasswordPermission.READ
    )


def test_given_already_shared_password_when_sharing_again_should_maintain_access(
    use_case: ShareAccessUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password,
):
    # Arrange
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    owner_group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    target_group_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    password_repository.save(password)
    # Set owner group
    password_permissions_repository.set_owner(owner_group_id, password.id)
    group_access_gateway.set_group_owner(owner_group_id, owner_id)
    # Already grant access to target group
    password_permissions_repository.grant_access(
        target_group_id, password.id, PasswordPermission.READ
    )
    group_access_gateway.set_group_owner(
        target_group_id, UUID("9d742e0e-bb76-4728-83ef-8d546d7c62e7")
    )

    # Act: Share again
    use_case.execute(ShareResourceCommand(owner_id, target_group_id, password.id))

    # Assert: Still has access
    assert password_permissions_repository.has_access(
        target_group_id, password.id, PasswordPermission.READ
    )


def test_given_non_existing_password_when_sharing_access_should_raise_password_not_found_error(
    use_case: ShareAccessUseCase,
):
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    password_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    with pytest.raises(PasswordNotFoundError):
        use_case.execute(ShareResourceCommand(owner_id, user_id, password_id))
