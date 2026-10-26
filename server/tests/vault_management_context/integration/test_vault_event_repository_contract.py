"""Reading audit events back behaves the same on the fake and on SQL."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tests.vault_management_context.unit.fakes import FakeVaultEventRepository
from vault_management_context.adapters.secondary import SqlVaultEventRepository

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


@pytest.fixture(params=["fake", "sql"])
def repository(request, session):
    if request.param == "fake":
        return FakeVaultEventRepository()
    return SqlVaultEventRepository(session)


def _append(repository, event_type: str, occurred_on: datetime, event_data: dict | None = None) -> None:
    repository.append_event(
        event_id=uuid4(),
        event_type=event_type,
        occurred_on=occurred_on,
        actor_user_id=None,
        event_data=event_data or {},
    )


def test_list_events_returns_only_the_given_types_oldest_first(repository):
    _append(repository, "VaultShareLinkRetrievedEvent", NOW + timedelta(minutes=5), {"share_index": 2})
    _append(repository, "VaultLockedEvent", NOW + timedelta(minutes=3))
    _append(repository, "VaultCreatedEvent", NOW, {"setup_id": "s1", "nb_shares": 3, "threshold": 2})

    events = repository.list_events(["VaultCreatedEvent", "VaultShareLinkRetrievedEvent"])

    assert [e.event_type for e in events] == ["VaultCreatedEvent", "VaultShareLinkRetrievedEvent"]
    assert events[0].occurred_on == NOW
    assert events[0].event_data == {"setup_id": "s1", "nb_shares": 3, "threshold": 2}
    assert events[1].event_data == {"share_index": 2}


def test_list_events_returns_nothing_for_unknown_types(repository):
    _append(repository, "VaultCreatedEvent", NOW)

    assert repository.list_events(["SomethingElse"]) == []
