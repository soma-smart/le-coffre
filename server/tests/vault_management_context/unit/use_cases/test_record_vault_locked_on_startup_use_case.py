from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from tests.fakes.fake_domain_event_publisher import FakeDomainEventPublisher
from vault_management_context.application.use_cases import RecordVaultLockedOnStartupUseCase
from vault_management_context.domain.events import VaultLockedEvent

from ..fakes import FakeVaultEventRepository, FakeVaultRepository


@pytest.fixture()
def use_case(vault_repository, event_publisher, vault_event_repository):
    return RecordVaultLockedOnStartupUseCase(vault_repository, event_publisher, vault_event_repository)


def _stored(vault_event_repository: FakeVaultEventRepository, event_type: str, minutes_ago: int) -> None:
    vault_event_repository.append_event(
        event_id=uuid4(),
        event_type=event_type,
        occurred_on=datetime.now() - timedelta(minutes=minutes_ago),
        actor_user_id=None,
        event_data={},
    )


def _published_locks(event_publisher: FakeDomainEventPublisher) -> list[VaultLockedEvent]:
    return event_publisher.get_published_events_of_type(VaultLockedEvent)


def test_given_no_vault_when_starting_should_record_nothing(use_case, event_publisher, vault_event_repository):
    use_case.execute()

    assert _published_locks(event_publisher) == []
    assert vault_event_repository.events == []


@pytest.mark.parametrize("last_event_type", ["VaultUnlockedEvent", "VaultCreatedEvent"])
def test_given_vault_last_known_unlocked_when_starting_should_record_and_publish_a_lock(
    use_case, vault_repository: FakeVaultRepository, event_publisher, vault_event_repository, last_event_type
):
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    _stored(vault_event_repository, "VaultLockedEvent", minutes_ago=10)
    _stored(vault_event_repository, last_event_type, minutes_ago=5)

    use_case.execute()

    locks = _published_locks(event_publisher)
    assert len(locks) == 1
    assert locks[0].locked_by_user_id is None
    stored = vault_event_repository.events[-1]
    assert stored["event_type"] == "VaultLockedEvent"
    assert stored["actor_user_id"] is None
    assert stored["event_data"] == {"reason": "server_start"}


def test_given_vault_already_locked_when_starting_should_not_report_the_same_lock_again(
    use_case, vault_repository: FakeVaultRepository, event_publisher, vault_event_repository
):
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    _stored(vault_event_repository, "VaultUnlockedEvent", minutes_ago=10)
    _stored(vault_event_repository, "VaultLockedEvent", minutes_ago=5)

    use_case.execute()

    assert _published_locks(event_publisher) == []


def test_given_server_restarting_in_a_loop_should_report_the_lock_once(
    use_case, vault_repository: FakeVaultRepository, event_publisher, vault_event_repository
):
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    _stored(vault_event_repository, "VaultUnlockedEvent", minutes_ago=10)

    for _ in range(3):
        use_case.execute()

    assert len(_published_locks(event_publisher)) == 1


def test_given_vault_with_no_recorded_state_when_starting_should_record_a_lock(
    use_case, vault_repository: FakeVaultRepository, event_publisher
):
    # A vault set up before vault events were recorded.
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)

    use_case.execute()

    assert len(_published_locks(event_publisher)) == 1


def test_given_recording_the_lock_fails_should_not_publish_it(
    use_case, vault_repository: FakeVaultRepository, event_publisher, vault_event_repository: FakeVaultEventRepository
):
    # Regression: append_event() must run before publish(), not after. The DB is
    # least stable right on the startup path (just after migrations); if the append
    # fails, no email must go out for a lock that was never durably recorded — the
    # next start would otherwise find the same "last known unlocked" state and
    # report (and email) the same lock again.
    vault_repository.save_vault_with_shares(nb_shares=3, threshold=2)
    vault_event_repository.fail_next_append()

    with pytest.raises(RuntimeError):
        use_case.execute()

    assert _published_locks(event_publisher) == []
