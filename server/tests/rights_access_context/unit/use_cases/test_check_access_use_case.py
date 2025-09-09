import pytest
from uuid import UUID

from rights_access_context.application.use_cases import (
    CheckAccessUseCase,
)
from ..mocks import FakeRightsRepository
from rights_access_context.domain.value_objects import Permission
from shared_kernel.access_control import Granted

# Test data constants
USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
RESOURCE_ID = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")


@pytest.fixture()
def use_case(rights_repository: FakeRightsRepository):
    return CheckAccessUseCase(rights_repository)


def test_given_owned_resource_when_reading_should_grant_access(
    use_case: CheckAccessUseCase, rights_repository: FakeRightsRepository
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    rights_repository.add_permission(user_id, resource_id, Permission.READ)

    result = use_case.execute(user_id, resource_id, Permission.READ)

    assert result.granted is Granted.ACCESS


def test_given_not_owned_resource_when_reading_should_deny_access(
    use_case: CheckAccessUseCase,
):
    user_id = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
    resource_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    result = use_case.execute(user_id, resource_id)

    assert result.granted is Granted.NOT_FOUND


@pytest.mark.parametrize(
    "permission", [Permission.READ, Permission.UPDATE, Permission.DELETE]
)
def test_should_grant_access_when_user_has_required_permission(
    use_case, rights_repository, permission
):
    # ARRANGE
    rights_repository.add_permission(USER_ID, RESOURCE_ID, permission)

    # ACT
    result = use_case.execute(USER_ID, RESOURCE_ID, permission)

    # ASSERT
    assert result.granted is Granted.ACCESS


@pytest.mark.parametrize(
    "granted_permission, requested_permission, expected_grant",
    [
        (Permission.READ, Permission.UPDATE, Granted.VIEW_ONLY),
        (Permission.READ, Permission.DELETE, Granted.VIEW_ONLY),
        (Permission.UPDATE, Permission.DELETE, Granted.NOT_FOUND),
    ],
)
def test_should_deny_access_when_user_has_insufficient_permission(
    use_case,
    rights_repository,
    granted_permission,
    requested_permission,
    expected_grant,
):
    # ARRANGE
    rights_repository.add_permission(USER_ID, RESOURCE_ID, granted_permission)

    # ACT
    result = use_case.execute(USER_ID, RESOURCE_ID, requested_permission)

    # ASSERT
    assert result.granted is expected_grant


def test_when_user_has_read_and_update_request_delete_then_view_only(
    use_case: CheckAccessUseCase, rights_repository: FakeRightsRepository
):
    rights_repository.add_permission(USER_ID, RESOURCE_ID, Permission.READ)
    rights_repository.add_permission(USER_ID, RESOURCE_ID, Permission.UPDATE)

    result = use_case.execute(USER_ID, RESOURCE_ID, Permission.DELETE)

    assert result.granted is Granted.VIEW_ONLY
