"""Password events are stored in naive UTC, like IamEvent, so the two tables share one clock."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from password_management_context.adapters.secondary.sql import SqlPasswordEventRepository
from password_management_context.adapters.secondary.sql.model.password_event import PasswordEventTable
from password_management_context.domain.events import PasswordAccessedEvent

PARIS_SUMMER = timezone(timedelta(hours=2))


@pytest.fixture
def repository(session):
    return SqlPasswordEventRepository(session)


def _append(repository, password_id, occurred_on, actor_principal_id=None):
    event_id = uuid4()
    repository.append_event(
        event_id=event_id,
        event_type="PasswordAccessedEvent",
        occurred_on=occurred_on,
        password_id=password_id,
        actor_principal_id=actor_principal_id or uuid4(),
        event_data={},
    )
    return event_id


def test_given_an_aware_timestamp_when_appending_then_it_is_stored_as_naive_utc(repository, session):
    event_id = _append(repository, uuid4(), datetime(2026, 1, 1, 14, 0, tzinfo=PARIS_SUMMER))

    assert session.get(PasswordEventTable, event_id).occurred_on == datetime(2026, 1, 1, 12, 0)


def test_given_aware_bounds_when_filtering_then_they_are_compared_in_utc(repository):
    password_id = uuid4()
    _append(repository, password_id, datetime(2026, 1, 1, 12, 0, tzinfo=UTC))

    # 13:30+02:00 is 11:30 UTC, before the event: compared as a wall clock, it would come after it.
    events = repository.list_events(password_id, start_date=datetime(2026, 1, 1, 13, 30, tzinfo=PARIS_SUMMER))

    assert len(events) == 1


@pytest.mark.parametrize(
    "bounds",
    [
        pytest.param({"start_date": datetime(1, 1, 1, tzinfo=timezone(timedelta(hours=5)))}, id="first-day"),
        pytest.param({"end_date": datetime(9999, 12, 31, 23, 59, tzinfo=timezone(timedelta(hours=-5)))}, id="last-day"),
    ],
)
def test_given_a_bound_at_the_edge_of_the_calendar_when_filtering_then_it_excludes_nothing(repository, bounds):
    """Such a bound has no UTC equivalent: it must not fail the request."""
    password_id, actor_id = uuid4(), uuid4()
    _append(repository, password_id, datetime(2026, 1, 1, 12, 0, tzinfo=UTC), actor_id)

    assert len(repository.list_events(password_id, **bounds)) == 1
    assert len(repository.list_events_by_actor(actor_id, **bounds)) == 1


def test_given_no_timestamp_when_creating_an_event_then_it_is_dated_in_utc():
    event = PasswordAccessedEvent(
        password_id=uuid4(), password_name="deploy-key", accessed_by_principal_id=uuid4(), credential_id=None
    )

    assert event.occurred_on.utcoffset() == timedelta(0)
