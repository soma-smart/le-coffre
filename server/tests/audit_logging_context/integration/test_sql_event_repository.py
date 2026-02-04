from uuid import uuid4
from datetime import datetime

from password_management_context.domain.events import (
    PasswordCreatedEvent,
    PasswordDeletedEvent,
)
from shared_kernel.domain.value_objects import EventPriority


def test_should_save_and_retrieve_event(sql_event_repository):
    # Arrange
    event_id = uuid4()
    password_id = uuid4()
    group_id = uuid4()
    user_id = uuid4()
    occurred_on = datetime(2024, 1, 15, 10, 30, 0)

    event = PasswordCreatedEvent(
        event_id=event_id,
        password_id=password_id,
        password_name="Test Password",
        owner_group_id=group_id,
        created_by_user_id=user_id,
        folder="work",
        occurred_on=occurred_on,
    )

    # Act
    sql_event_repository.append_event(event)
    retrieved_events = sql_event_repository.list_events()

    # Assert
    assert len(retrieved_events) == 1
    retrieved = retrieved_events[0]
    assert retrieved.event_id == event_id
    assert retrieved.event_type == "PasswordCreatedEvent"
    assert retrieved.occurred_on == occurred_on
    assert retrieved.priority == EventPriority.HIGH


def test_should_store_multiple_events_in_order(sql_event_repository):
    # Arrange
    event1_time = datetime(2024, 1, 15, 10, 0, 0)
    event2_time = datetime(2024, 1, 15, 11, 0, 0)
    event3_time = datetime(2024, 1, 15, 9, 0, 0)  # Earlier

    event1 = PasswordCreatedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        password_name="Password 1",
        owner_group_id=uuid4(),
        created_by_user_id=uuid4(),
        occurred_on=event1_time,
    )
    event2 = PasswordCreatedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        password_name="Password 2",
        owner_group_id=uuid4(),
        created_by_user_id=uuid4(),
        occurred_on=event2_time,
    )
    event3 = PasswordDeletedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        deleted_by_user_id=uuid4(),
        owner_group_id=uuid4(),
        occurred_on=event3_time,
    )

    # Act
    sql_event_repository.append_event(event1)
    sql_event_repository.append_event(event2)
    sql_event_repository.append_event(event3)
    retrieved_events = sql_event_repository.list_events()

    # Assert
    assert len(retrieved_events) == 3
    # Should be ordered by occurred_on
    assert retrieved_events[0].occurred_on == event3_time
    assert retrieved_events[1].occurred_on == event1_time
    assert retrieved_events[2].occurred_on == event2_time


def test_should_return_empty_list_when_no_events(sql_event_repository):
    # Arrange - no events added

    # Act
    retrieved_events = sql_event_repository.list_events()

    # Assert
    assert retrieved_events == []
    assert len(retrieved_events) == 0


def test_should_filter_events_by_type(sql_event_repository):
    # Arrange - create events of different types
    created_event = PasswordCreatedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        password_name="Password 1",
        owner_group_id=uuid4(),
        created_by_user_id=uuid4(),
        occurred_on=datetime(2024, 1, 15, 10, 0, 0),
    )
    deleted_event = PasswordDeletedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        deleted_by_user_id=uuid4(),
        owner_group_id=uuid4(),
        occurred_on=datetime(2024, 1, 15, 11, 0, 0),
    )
    another_created = PasswordCreatedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        password_name="Password 2",
        owner_group_id=uuid4(),
        created_by_user_id=uuid4(),
        occurred_on=datetime(2024, 1, 15, 12, 0, 0),
    )

    sql_event_repository.append_event(created_event)
    sql_event_repository.append_event(deleted_event)
    sql_event_repository.append_event(another_created)

    # Act - filter by PasswordCreatedEvent only
    filtered_events = sql_event_repository.list_events(
        event_types=["PasswordCreatedEvent"]
    )

    # Assert
    assert len(filtered_events) == 2
    assert all(event.event_type == "PasswordCreatedEvent" for event in filtered_events)


def test_should_filter_events_by_multiple_types(sql_event_repository):
    # Arrange - create events of different types
    created_event = PasswordCreatedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        password_name="Password 1",
        owner_group_id=uuid4(),
        created_by_user_id=uuid4(),
        occurred_on=datetime(2024, 1, 15, 10, 0, 0),
    )
    deleted_event1 = PasswordDeletedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        deleted_by_user_id=uuid4(),
        owner_group_id=uuid4(),
        occurred_on=datetime(2024, 1, 15, 11, 0, 0),
    )
    deleted_event2 = PasswordDeletedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        deleted_by_user_id=uuid4(),
        owner_group_id=uuid4(),
        occurred_on=datetime(2024, 1, 15, 12, 0, 0),
    )

    sql_event_repository.append_event(created_event)
    sql_event_repository.append_event(deleted_event1)
    sql_event_repository.append_event(deleted_event2)

    # Act - filter by both PasswordCreatedEvent and PasswordDeletedEvent
    filtered_events = sql_event_repository.list_events(
        event_types=["PasswordCreatedEvent", "PasswordDeletedEvent"]
    )

    # Assert
    assert len(filtered_events) == 3
    event_types = {event.event_type for event in filtered_events}
    assert event_types == {"PasswordCreatedEvent", "PasswordDeletedEvent"}


def test_should_filter_events_by_user_id(sql_event_repository):
    # Arrange - create events with different user IDs
    user_id_1 = uuid4()
    user_id_2 = uuid4()
    group_id = uuid4()

    created_by_user_1 = PasswordCreatedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        password_name="Password 1",
        owner_group_id=group_id,
        created_by_user_id=user_id_1,
        occurred_on=datetime(2024, 1, 15, 10, 0, 0),
    )
    deleted_by_user_2 = PasswordDeletedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        deleted_by_user_id=user_id_2,
        owner_group_id=group_id,
        occurred_on=datetime(2024, 1, 15, 11, 0, 0),
    )
    created_by_user_1_again = PasswordCreatedEvent(
        event_id=uuid4(),
        password_id=uuid4(),
        password_name="Password 2",
        owner_group_id=group_id,
        created_by_user_id=user_id_1,
        occurred_on=datetime(2024, 1, 15, 12, 0, 0),
    )

    sql_event_repository.append_event(created_by_user_1)
    sql_event_repository.append_event(deleted_by_user_2)
    sql_event_repository.append_event(created_by_user_1_again)

    # Act - filter by user_id_1
    filtered_events = sql_event_repository.list_events(user_id=user_id_1)

    # Assert
    assert len(filtered_events) == 2
    assert all(event.event_type == "PasswordCreatedEvent" for event in filtered_events)
