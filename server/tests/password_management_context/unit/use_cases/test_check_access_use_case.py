import pytest
from uuid import UUID

from password_management_context.application.commands import CheckAccessCommand
from password_management_context.application.use_cases import (
    CheckAccessUseCase,
)
from ..fakes import FakePasswordPermissionsRepository
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.access_control import Granted

# Test data constants
USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
RESOURCE_ID = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")


@pytest.fixture()
def use_case(password_permissions_repository: FakePasswordPermissionsRepository):
    return CheckAccessUseCase(password_permissions_repository)


def test_given_user_with_read_permission_when_checking_access_should_grant_access(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    password_permissions_repository.grant_access(
        USER_ID, RESOURCE_ID, PasswordPermission.READ
    )

    command = CheckAccessCommand(
        user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ
    )
    result = use_case.execute(command)

    assert result.granted is Granted.ACCESS


def test_given_user_without_permission_when_checking_access_should_deny_access(
    use_case: CheckAccessUseCase,
):
    command = CheckAccessCommand(
        user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ
    )
    result = use_case.execute(command)

    assert result.granted is Granted.NOT_FOUND
