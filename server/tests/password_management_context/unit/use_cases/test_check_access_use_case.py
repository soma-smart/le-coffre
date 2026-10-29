from datetime import timedelta
from uuid import UUID

import pytest

from password_management_context.application.commands import CheckAccessCommand
from password_management_context.application.use_cases import (
    CheckAccessUseCase,
)
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.domain.value_objects import Granted
from tests.shared_kernel.fakes.fake_time_gateway import FakeTimeGateway

from ..conftest import NOW
from ..fakes import FakePasswordPermissionsRepository

# Test data constants
USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
RESOURCE_ID = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")


@pytest.fixture()
def use_case(password_permissions_repository: FakePasswordPermissionsRepository, time_gateway: FakeTimeGateway):
    return CheckAccessUseCase(password_permissions_repository, time_gateway)


def test_given_user_with_read_permission_when_checking_access_should_grant_access(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    password_permissions_repository.grant_access(USER_ID, RESOURCE_ID, PasswordPermission.READ)

    command = CheckAccessCommand(user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ)
    result = use_case.execute(command)

    assert result.granted is Granted.ACCESS


def test_given_user_without_permission_when_checking_access_should_deny_access(
    use_case: CheckAccessUseCase,
):
    command = CheckAccessCommand(user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ)
    result = use_case.execute(command)

    assert result.granted is Granted.NOT_FOUND


def test_given_share_past_its_deadline_when_checking_access_should_deny_access(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    password_permissions_repository.grant_access(
        USER_ID, RESOURCE_ID, PasswordPermission.READ, expires_at=NOW - timedelta(minutes=1)
    )

    command = CheckAccessCommand(user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ)
    result = use_case.execute(command)

    assert result.granted is Granted.NOT_FOUND


def test_given_share_reaching_its_deadline_now_when_checking_access_should_deny_access(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    password_permissions_repository.grant_access(USER_ID, RESOURCE_ID, PasswordPermission.READ, expires_at=NOW)

    command = CheckAccessCommand(user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ)
    result = use_case.execute(command)

    assert result.granted is Granted.NOT_FOUND


def test_given_share_before_its_deadline_when_checking_access_should_grant_access(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    password_permissions_repository.grant_access(
        USER_ID, RESOURCE_ID, PasswordPermission.READ, expires_at=NOW + timedelta(minutes=1)
    )

    command = CheckAccessCommand(user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ)
    result = use_case.execute(command)

    assert result.granted is Granted.ACCESS
    assert result.is_owner is False


def test_given_owner_when_checking_access_should_grant_access_as_owner(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    password_permissions_repository.set_owner(USER_ID, RESOURCE_ID)

    command = CheckAccessCommand(user_id=USER_ID, resource_id=RESOURCE_ID, permission=PasswordPermission.READ)
    result = use_case.execute(command)

    assert result.granted is Granted.ACCESS
    assert result.is_owner is True
