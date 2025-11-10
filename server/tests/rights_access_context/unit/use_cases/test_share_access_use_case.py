from uuid import UUID
import pytest
from rights_access_context.application.use_cases import (
    ShareAccessUseCase,
)
from ..fakes import FakeRightsRepository, FakeUserManagementGateway
from rights_access_context.application.commands import ShareResourceCommand
from rights_access_context.domain.exceptions import PermissionDeniedError
from rights_access_context.domain.value_objects import Permission
from shared_kernel.domain import UserNotFoundError


@pytest.fixture()
def use_case(
    rights_repository: FakeRightsRepository,
    user_management_gateway: FakeUserManagementGateway,
):
    return ShareAccessUseCase(rights_repository, user_management_gateway)


def test_given_owner_when_sharing_should_grant_read_access(
    use_case: ShareAccessUseCase,
    rights_repository: FakeRightsRepository,
    user_management_gateway: FakeUserManagementGateway,
):
    # Arrange: Given an owner of a resource
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    rights_repository.set_owner(owner_id, resource_id)
    user_management_gateway.add_user(owner_id)
    user_management_gateway.add_user(user_id)

    # Act: When owner shares the resource
    use_case.execute(ShareResourceCommand(owner_id, user_id, resource_id))

    # Assert: Then the recipient should have READ access only
    assert (
        rights_repository.has_permission(user_id, resource_id, Permission.READ) is True
    )
    assert (
        rights_repository.has_permission(user_id, resource_id, Permission.UPDATE)
        is False
    )
    assert (
        rights_repository.has_permission(user_id, resource_id, Permission.DELETE)
        is False
    )


def test_given_non_owner_with_permissions_when_sharing_should_fail(
    use_case: ShareAccessUseCase,
    rights_repository: FakeRightsRepository,
    user_management_gateway: FakeUserManagementGateway,
):
    # Arrange: Given a user with UPDATE permission but not owner
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    non_owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    third_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e8")

    rights_repository.set_owner(owner_id, resource_id)
    rights_repository.add_permission(non_owner_id, resource_id, Permission.UPDATE)
    user_management_gateway.add_user(owner_id)
    user_management_gateway.add_user(non_owner_id)
    user_management_gateway.add_user(third_user_id)

    # Act & Assert: When non-owner tries to share, then should fail
    with pytest.raises(PermissionDeniedError):
        use_case.execute(ShareResourceCommand(non_owner_id, third_user_id, resource_id))

    # Assert: Third user should not have access
    assert (
        rights_repository.has_permission(third_user_id, resource_id, Permission.READ)
        is False
    )


def test_given_owner_when_sharing_already_shared_resource_should_succeed(
    use_case: ShareAccessUseCase,
    rights_repository: FakeRightsRepository,
    user_management_gateway: FakeUserManagementGateway,
):
    # Arrange: Given a resource already shared with a user
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")
    rights_repository.set_owner(owner_id, resource_id)
    rights_repository.add_permission(user_id, resource_id, Permission.READ)
    user_management_gateway.add_user(owner_id)
    user_management_gateway.add_user(user_id)

    # Act: When owner shares again with the same user
    use_case.execute(ShareResourceCommand(owner_id, user_id, resource_id))

    # Assert: Then it should succeed (idempotent) and user still has READ access
    assert (
        rights_repository.has_permission(user_id, resource_id, Permission.READ) is True
    )


def test_given_owner_when_sharing_with_nonexistent_user_should_fail(
    use_case: ShareAccessUseCase,
    rights_repository: FakeRightsRepository,
    user_management_gateway: FakeUserManagementGateway,
):
    # Arrange: Given an owner of a resource
    owner_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e7")
    nonexistent_user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e6")

    rights_repository.set_owner(owner_id, resource_id)
    user_management_gateway.add_user(owner_id)  # Owner exists
    # nonexistent_user_id is NOT added to gateway

    # Act & Assert: When owner tries to share with non-existent user, then should fail
    with pytest.raises(UserNotFoundError):
        use_case.execute(
            ShareResourceCommand(owner_id, nonexistent_user_id, resource_id)
        )

    # Assert: Non-existent user should not have access
    assert (
        rights_repository.has_permission(
            nonexistent_user_id, resource_id, Permission.READ
        )
        is False
    )
