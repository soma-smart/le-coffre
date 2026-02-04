import pytest
from uuid import uuid4
from datetime import datetime

from audit_logging_context.application.use_cases.list_event_use_case import (
    ListEventUseCase,
)
from audit_logging_context.application.commands import ListEventCommand
from password_management_context.domain.events import (
    PasswordCreatedEvent,
    PasswordDeletedEvent,
    PasswordUpdatedEvent,
)
from shared_kernel.domain.entities import DomainEvent, AuthenticatedUser
from shared_kernel.adapters.primary.exceptions import NotAdminError


@pytest.fixture
def use_case(event_repository):
    return ListEventUseCase(event_repository)


@pytest.fixture
def admin_user():
    return AuthenticatedUser(user_id=uuid4(), roles=["admin"])


@pytest.fixture
def regular_user():
    return AuthenticatedUser(user_id=uuid4(), roles=["user"])


def test_given_empty_event_list_when_admin_lists_events_then_return_empty_list(
    use_case, admin_user
):
    command = ListEventCommand(requesting_user=admin_user)
    response = use_case.execute(command)

    assert response.events == []


def test_given_non_empty_event_list_when_admin_lists_events_then_return_event_list(
    use_case,
    event_repository,
    admin_user,
):
    event1 = DomainEvent(uuid4(), datetime.now())
    event_repository.append_event(event1)
    command = ListEventCommand(requesting_user=admin_user)

    response = use_case.execute(command)

    assert len(response.events) == 1
    assert response.events[0].event_id == event1.event_id
    assert response.events[0].event_type == event1.event_type
    assert response.events[0].priority == event1.priority


def test_given_non_admin_user_when_listing_events_then_raise_not_admin_error(
    use_case, regular_user
):
    command = ListEventCommand(requesting_user=regular_user)

    with pytest.raises(NotAdminError) as exc_info:
        use_case.execute(command)

    assert "administrators" in str(exc_info.value).lower()


def test_given_events_when_filtering_by_type_then_return_only_matching_events(
    use_case, event_repository, admin_user
):
    # Create events with different types
    event1 = DomainEvent(uuid4(), datetime.now())
    event1.event_type = "PasswordCreatedEvent"
    event2 = DomainEvent(uuid4(), datetime.now())
    event2.event_type = "PasswordDeletedEvent"
    event3 = DomainEvent(uuid4(), datetime.now())
    event3.event_type = "PasswordCreatedEvent"

    event_repository.append_event(event1)
    event_repository.append_event(event2)
    event_repository.append_event(event3)

    # Filter by PasswordCreatedEvent only
    command = ListEventCommand(
        requesting_user=admin_user, event_types=["PasswordCreatedEvent"]
    )

    response = use_case.execute(command)

    assert len(response.events) == 2
    assert all(event.event_type == "PasswordCreatedEvent" for event in response.events)


def test_given_events_when_filtering_by_multiple_types_then_return_all_matching(
    use_case, event_repository, admin_user
):
    # Create events with different types
    event1 = DomainEvent(uuid4(), datetime.now())
    event1.event_type = "PasswordCreatedEvent"
    event2 = DomainEvent(uuid4(), datetime.now())
    event2.event_type = "PasswordDeletedEvent"
    event3 = DomainEvent(uuid4(), datetime.now())
    event3.event_type = "PasswordUpdatedEvent"

    event_repository.append_event(event1)
    event_repository.append_event(event2)
    event_repository.append_event(event3)

    # Filter by PasswordCreatedEvent and PasswordDeletedEvent
    command = ListEventCommand(
        requesting_user=admin_user,
        event_types=["PasswordCreatedEvent", "PasswordDeletedEvent"],
    )

    response = use_case.execute(command)

    assert len(response.events) == 2
    event_types = {event.event_type for event in response.events}
    assert event_types == {"PasswordCreatedEvent", "PasswordDeletedEvent"}


def test_given_events_when_filtering_by_date_range_then_return_only_matching_events(
    use_case, event_repository, admin_user
):
    # Create events with different dates
    event1 = DomainEvent(uuid4(), datetime(2024, 1, 15, 10, 0, 0))
    event1.event_type = "PasswordCreatedEvent"
    event2 = DomainEvent(uuid4(), datetime(2024, 1, 16, 10, 0, 0))
    event2.event_type = "PasswordDeletedEvent"
    event3 = DomainEvent(uuid4(), datetime(2024, 1, 17, 10, 0, 0))
    event3.event_type = "PasswordCreatedEvent"

    event_repository.append_event(event1)
    event_repository.append_event(event2)
    event_repository.append_event(event3)

    # Filter by date range (Jan 15-16)
    command = ListEventCommand(
        requesting_user=admin_user,
        start_date=datetime(2024, 1, 15, 0, 0, 0),
        end_date=datetime(2024, 1, 16, 23, 59, 59),
    )

    response = use_case.execute(command)

    assert len(response.events) == 2
    assert all(
        datetime(2024, 1, 15) <= event.occurred_on <= datetime(2024, 1, 16, 23, 59, 59)
        for event in response.events
    )


def test_given_events_when_filtering_by_start_date_only_then_return_events_after(
    use_case, event_repository, admin_user
):
    # Create events with different dates
    event1 = DomainEvent(uuid4(), datetime(2024, 1, 15, 10, 0, 0))
    event1.event_type = "PasswordCreatedEvent"
    event2 = DomainEvent(uuid4(), datetime(2024, 1, 16, 10, 0, 0))
    event2.event_type = "PasswordDeletedEvent"
    event3 = DomainEvent(uuid4(), datetime(2024, 1, 17, 10, 0, 0))
    event3.event_type = "PasswordCreatedEvent"

    event_repository.append_event(event1)
    event_repository.append_event(event2)
    event_repository.append_event(event3)

    # Filter by start date only
    command = ListEventCommand(
        requesting_user=admin_user,
        start_date=datetime(2024, 1, 16, 0, 0, 0),
    )

    response = use_case.execute(command)

    assert len(response.events) == 2
    assert all(event.occurred_on >= datetime(2024, 1, 16) for event in response.events)


def test_given_events_when_filtering_by_user_id_then_return_only_matching_events(
    use_case, event_repository, admin_user
):
    # Create events with different user IDs
    user_id_1 = uuid4()
    user_id_2 = uuid4()
    group_id = uuid4()

    event1 = PasswordCreatedEvent(
        password_id=uuid4(),
        password_name="Password 1",
        owner_group_id=group_id,
        created_by_user_id=user_id_1,
        occurred_on=datetime.now(),
    )

    event2 = PasswordDeletedEvent(
        password_id=uuid4(),
        deleted_by_user_id=user_id_2,
        owner_group_id=group_id,
        occurred_on=datetime.now(),
    )

    event3 = PasswordUpdatedEvent(
        password_id=uuid4(),
        updated_by_user_id=user_id_1,
        has_name_changed=True,
        has_password_changed=False,
        has_folder_changed=False,
        occurred_on=datetime.now(),
    )

    event_repository.append_event(event1)
    event_repository.append_event(event2)
    event_repository.append_event(event3)

    # Filter by user_id_1
    command = ListEventCommand(
        requesting_user=admin_user,
        user_id=user_id_1,
    )

    response = use_case.execute(command)

    assert len(response.events) == 2
    # Verify both events have user_id_1 extracted into the DTO
    for event_dto in response.events:
        assert event_dto.user_id == user_id_1
