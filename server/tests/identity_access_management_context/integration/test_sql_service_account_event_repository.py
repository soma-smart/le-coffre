from datetime import UTC, datetime
from uuid import uuid4

from identity_access_management_context.domain.events import (
    ServiceAccountCreatedEvent,
    ServiceAccountRevokedEvent,
    ServiceAccountsListedEvent,
)
from identity_access_management_context.domain.value_objects import ServiceAccountToken

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _created(service_account_id, user_id, name="nightly-backup", occurred_on=NOW):
    return ServiceAccountCreatedEvent(
        event_id=uuid4(),
        occurred_on=occurred_on,
        user_id=user_id,
        service_account_id=service_account_id,
        service_account_name=name,
    )


def test_given_a_creation_event_when_reading_facts_back_then_they_round_trip(
    sql_service_account_event_repository, session
):
    account_id, user_id = uuid4(), uuid4()
    sql_service_account_event_repository.extend([_created(account_id, user_id)])
    session.expunge_all()

    (fact,) = sql_service_account_event_repository.get_creation_facts([account_id])

    assert fact.created_by_user_id == user_id
    assert fact.created_at == NOW


def test_given_a_creation_event_when_reading_facts_back_then_the_timestamp_is_timezone_aware(
    sql_service_account_event_repository, session
):
    """The column is naive, and a naive value reaching the domain is a bug rather than a conversion."""
    account_id = uuid4()
    sql_service_account_event_repository.extend([_created(account_id, uuid4())])
    session.expunge_all()

    (fact,) = sql_service_account_event_repository.get_creation_facts([account_id])

    assert fact.created_at.tzinfo is not None


def test_given_an_account_with_no_creation_event_when_reading_facts_then_its_slot_is_empty(
    sql_service_account_event_repository,
):
    known, unknown = uuid4(), uuid4()
    sql_service_account_event_repository.extend([_created(known, uuid4())])

    facts = sql_service_account_event_repository.get_creation_facts([unknown, known])

    assert facts[0].created_at is None
    assert facts[0].created_by_user_id is None
    assert facts[1].created_at == NOW


def test_given_several_accounts_when_reading_facts_then_they_come_back_in_the_requested_order(
    sql_service_account_event_repository,
):
    first, second, third = uuid4(), uuid4(), uuid4()
    users = {first: uuid4(), second: uuid4(), third: uuid4()}
    sql_service_account_event_repository.extend([_created(account_id, user) for account_id, user in users.items()])

    facts = sql_service_account_event_repository.get_creation_facts([third, first, second])

    assert [f.created_by_user_id for f in facts] == [users[third], users[first], users[second]]


def test_given_no_ids_when_reading_facts_then_nothing_is_queried(sql_service_account_event_repository):
    assert sql_service_account_event_repository.get_creation_facts([]) == []


def test_given_other_service_account_events_when_reading_facts_then_only_creations_count(
    sql_service_account_event_repository,
):
    """Revocations and listings share the table; folding them in would misreport who created the account."""
    account_id, creator, revoker = uuid4(), uuid4(), uuid4()
    sql_service_account_event_repository.extend(
        [
            _created(account_id, creator),
            ServiceAccountRevokedEvent(
                event_id=uuid4(),
                occurred_on=NOW,
                user_id=revoker,
                service_account_id=account_id,
                service_account_name="nightly-backup",
            ),
            ServiceAccountsListedEvent(event_id=uuid4(), occurred_on=NOW, user_id=revoker, group_id=uuid4()),
        ]
    )

    (fact,) = sql_service_account_event_repository.get_creation_facts([account_id])

    assert fact.created_by_user_id == creator


def test_given_stored_events_then_no_token_or_hash_reaches_the_audit_rows(
    sql_service_account_event_repository, session
):
    import json

    from sqlmodel import select

    from identity_access_management_context.adapters.secondary.sql import IamEventTable

    token = ServiceAccountToken.generate()
    sql_service_account_event_repository.extend([_created(uuid4(), uuid4())])
    session.expunge_all()

    rows = session.exec(select(IamEventTable)).all()
    stored = json.dumps([row.event_data for row in rows])

    assert token.value not in stored
    assert token.hash not in stored
    assert "token" not in stored
