from datetime import datetime, timedelta
from uuid import uuid4

from vault_management_context.adapters.secondary import SqlVaultEventRepository


def test_get_last_event_type_should_return_the_most_recent_among_the_given_types(session):
    repository = SqlVaultEventRepository(session)
    now = datetime.now()
    for event_type, minutes_ago in [("VaultUnlockedEvent", 30), ("VaultLockedEvent", 20), ("VaultCreatedEvent", 5)]:
        repository.append_event(
            event_id=uuid4(),
            event_type=event_type,
            occurred_on=now - timedelta(minutes=minutes_ago),
            actor_user_id=None,
            event_data={},
        )

    assert repository.get_last_event_type(["VaultUnlockedEvent", "VaultLockedEvent"]) == "VaultLockedEvent"
    assert repository.get_last_event_type(["VaultCreatedEvent", "VaultLockedEvent"]) == "VaultCreatedEvent"
    assert repository.get_last_event_type(["SomethingElse"]) is None
