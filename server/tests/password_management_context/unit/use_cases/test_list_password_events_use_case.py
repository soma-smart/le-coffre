from datetime import datetime
from uuid import UUID

import pytest

from password_management_context.application.commands import (
    ListPasswordEventsCommand,
)
from password_management_context.application.use_cases import (
    ListPasswordEventsUseCase,
)
from password_management_context.domain.entities import Password
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    PasswordNotFoundError,
)
from password_management_context.domain.value_objects import PasswordPermission
from shared_kernel.domain.entities import AuthenticatedUser

from ..fakes import (
    FakeGroupAccessGateway,
    FakePasswordEventRepository,
    FakePasswordPermissionsRepository,
    FakePasswordRepository,
    FakeUserInfoGateway,
)

ADMIN_USER = AuthenticatedUser(user_id=UUID("7d742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=["admin"])

REGULAR_USER = AuthenticatedUser(user_id=UUID("9a742e0e-bb76-4728-83ef-8d546d7c62e5"), roles=[])


@pytest.fixture
def user_info_gateway():
    return FakeUserInfoGateway()


@pytest.fixture
def use_case(
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
    user_info_gateway: FakeUserInfoGateway,
):
    return ListPasswordEventsUseCase(
        password_repository,
        password_permissions_repository,
        group_access_gateway,
        password_event_repository,
        user_info_gateway,
    )


def test_should_return_events_when_admin_user(
    use_case: ListPasswordEventsUseCase,
    password_repository: FakePasswordRepository,
    password_event_repository: FakePasswordEventRepository,
):
    # Arrange - admin has NO group access, but should still see events
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    password = Password(
        id=password_id,
        name="Gmail",
        encrypted_value="encrypted(secret)",
        folder="default",
    )
    password_repository.save(password)

    # Add some events
    event1_id = UUID("a1111111-1111-1111-1111-111111111111")
    event2_id = UUID("b2222222-2222-2222-2222-222222222222")
    occurred_on1 = datetime(2026, 2, 6, 10, 0, 0)
    occurred_on2 = datetime(2026, 2, 6, 11, 0, 0)

    password_event_repository.append_event(
        event_id=event1_id,
        event_type="password.created",
        occurred_on=occurred_on1,
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={"title": "Gmail", "folder_id": None},
    )
    password_event_repository.append_event(
        event_id=event2_id,
        event_type="password.updated",
        occurred_on=occurred_on2,
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={"title": "Gmail Account", "folder_id": None},
    )

    # Act
    command = ListPasswordEventsCommand(
        password_id=password_id,
        requesting_user=ADMIN_USER,
    )
    response = use_case.execute(command)

    # Assert
    assert len(response.events) == 2
    # Events should be ordered by occurred_on desc (most recent first)
    assert response.events[0].event_id == str(event2_id)
    assert response.events[0].event_type == "password.updated"
    assert response.events[0].occurred_on == occurred_on2.isoformat()
    assert response.events[1].event_id == str(event1_id)
    assert response.events[1].event_type == "password.created"


def test_should_return_events_when_owner_has_group_access(
    use_case: ListPasswordEventsUseCase,
    password_repository: FakePasswordRepository,
    password_permissions_repository: FakePasswordPermissionsRepository,
    group_access_gateway: FakeGroupAccessGateway,
    password_event_repository: FakePasswordEventRepository,
):
    # Arrange
    group_id = UUID("8d742e0e-bb76-4728-83ef-8d546d7c62e9")
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    password_repository.save(
        Password(
            id=password_id,
            name="Gmail",
            encrypted_value="encrypted(secret)",
            folder="default",
        )
    )
    password_permissions_repository.grant_access(group_id, password_id, PasswordPermission.READ)
    group_access_gateway.set_group_owner(group_id, REGULAR_USER.user_id)

    password_event_repository.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="password.created",
        occurred_on=datetime(2026, 2, 6, 10, 0, 0),
        password_id=password_id,
        actor_user_id=REGULAR_USER.user_id,
        event_data={},
    )

    command = ListPasswordEventsCommand(
        password_id=password_id,
        requesting_user=REGULAR_USER,
    )
    response = use_case.execute(command)

    assert len(response.events) == 1
    assert response.events[0].event_type == "password.created"


def test_should_filter_events_by_event_types_when_specified(
    use_case: ListPasswordEventsUseCase,
    password_repository: FakePasswordRepository,
    password_event_repository: FakePasswordEventRepository,
):
    # Arrange
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    password_repository.save(
        Password(
            id=password_id,
            name="Gmail",
            encrypted_value="encrypted(secret)",
            folder="default",
        )
    )

    # Add multiple event types
    password_event_repository.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="password.created",
        occurred_on=datetime(2026, 2, 6, 10, 0, 0),
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={},
    )
    password_event_repository.append_event(
        event_id=UUID("b2222222-2222-2222-2222-222222222222"),
        event_type="password.accessed",
        occurred_on=datetime(2026, 2, 6, 11, 0, 0),
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={},
    )
    password_event_repository.append_event(
        event_id=UUID("c3333333-3333-3333-3333-333333333333"),
        event_type="password.updated",
        occurred_on=datetime(2026, 2, 6, 12, 0, 0),
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={},
    )

    # Act - Filter only accessed events
    command = ListPasswordEventsCommand(
        password_id=password_id,
        requesting_user=ADMIN_USER,
        event_types=["password.accessed"],
    )
    response = use_case.execute(command)

    # Assert
    assert len(response.events) == 1
    assert response.events[0].event_type == "password.accessed"


def test_should_filter_events_by_date_range_when_specified(
    use_case: ListPasswordEventsUseCase,
    password_repository: FakePasswordRepository,
    password_event_repository: FakePasswordEventRepository,
):
    # Arrange
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")

    password_repository.save(
        Password(
            id=password_id,
            name="Gmail",
            encrypted_value="encrypted(secret)",
            folder="default",
        )
    )

    # Add events at different times
    password_event_repository.append_event(
        event_id=UUID("a1111111-1111-1111-1111-111111111111"),
        event_type="password.created",
        occurred_on=datetime(2026, 2, 1, 10, 0, 0),
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={},
    )
    password_event_repository.append_event(
        event_id=UUID("b2222222-2222-2222-2222-222222222222"),
        event_type="password.accessed",
        occurred_on=datetime(2026, 2, 5, 11, 0, 0),
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={},
    )
    password_event_repository.append_event(
        event_id=UUID("c3333333-3333-3333-3333-333333333333"),
        event_type="password.updated",
        occurred_on=datetime(2026, 2, 10, 12, 0, 0),
        password_id=password_id,
        actor_user_id=ADMIN_USER.user_id,
        event_data={},
    )

    # Act - Filter events between Feb 4 and Feb 7
    command = ListPasswordEventsCommand(
        password_id=password_id,
        requesting_user=ADMIN_USER,
        start_date=datetime(2026, 2, 4, 0, 0, 0),
        end_date=datetime(2026, 2, 7, 23, 59, 59),
    )
    response = use_case.execute(command)

    # Assert
    assert len(response.events) == 1
    assert response.events[0].event_type == "password.accessed"


def test_should_raise_error_when_password_not_found(
    use_case: ListPasswordEventsUseCase,
):
    # Act & Assert
    with pytest.raises(PasswordNotFoundError):
        command = ListPasswordEventsCommand(
            password_id=UUID("00000000-0000-0000-0000-000000000000"),
            requesting_user=ADMIN_USER,
        )
        use_case.execute(command)


def test_given_non_admin_user_when_listing_events_should_raise_not_admin_error(
    use_case: ListPasswordEventsUseCase,
    password_repository: FakePasswordRepository,
):
    # Arrange - regular user with no group access
    password_id = UUID("e0e2eb69-5d6b-4500-947a-6636c8755b3f")
    password_repository.save(
        Password(
            id=password_id,
            name="Gmail",
            encrypted_value="encrypted(secret)",
            folder="default",
        )
    )

    # Act & Assert
    with pytest.raises(PasswordAccessDeniedError):
        command = ListPasswordEventsCommand(
            password_id=password_id,
            requesting_user=REGULAR_USER,
        )
        use_case.execute(command)
