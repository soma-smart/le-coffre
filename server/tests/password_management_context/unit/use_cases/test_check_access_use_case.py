import pytest
from uuid import UUID

from password_management_context.application.use_cases import (
    CheckAccessUseCase,
)
from ..fakes import FakePasswordPermissionsRepository
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.access_control import Granted
from password_management_context.domain.events import PasswordAccessCheckedEvent

# Test data constants
USER_ID = UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5")
RESOURCE_ID = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")


@pytest.fixture
def password_permissions_repository():
    return FakePasswordPermissionsRepository()


@pytest.fixture()
def use_case(
    password_permissions_repository,
    event_publisher,
):
    return CheckAccessUseCase(password_permissions_repository, event_publisher)


def test_given_owned_resource_when_reading_should_grant_access(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
):
    password_permissions_repository.grant_access(
        USER_ID, RESOURCE_ID, PasswordPermission.READ
    )

    result = use_case.execute(USER_ID, RESOURCE_ID, PasswordPermission.READ)

    assert result.granted is Granted.ACCESS


def test_given_not_owned_resource_when_reading_should_deny_access(
    use_case: CheckAccessUseCase,
):
    result = use_case.execute(USER_ID, RESOURCE_ID, PasswordPermission.READ)

    assert result.granted is Granted.NOT_FOUND


def test_should_publish_password_access_checked_event_when_access_is_granted(
    use_case: CheckAccessUseCase,
    password_permissions_repository: FakePasswordPermissionsRepository,
    event_publisher,
):
    password_permissions_repository.grant_access(
        USER_ID, RESOURCE_ID, PasswordPermission.READ
    )

    use_case.execute(USER_ID, RESOURCE_ID, PasswordPermission.READ)

    published_events = event_publisher.published_events
    assert len(published_events) == 1
    event = published_events[0]
    assert isinstance(event, PasswordAccessCheckedEvent)
    assert event.password_id == RESOURCE_ID
    assert event.checked_by_user_id == USER_ID
    assert event.has_access is True
    assert event.priority == "LOW"


def test_should_publish_password_access_checked_event_when_access_is_denied(
    use_case: CheckAccessUseCase,
    event_publisher,
):
    use_case.execute(USER_ID, RESOURCE_ID, PasswordPermission.READ)

    published_events = event_publisher.published_events
    assert len(published_events) == 1
    event = published_events[0]
    assert isinstance(event, PasswordAccessCheckedEvent)
    assert event.password_id == RESOURCE_ID
    assert event.checked_by_user_id == USER_ID
    assert event.has_access is False
    assert event.priority == "LOW"
