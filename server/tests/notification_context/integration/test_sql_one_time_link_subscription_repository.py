from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlmodel import Session

from notification_context.adapters.secondary.sql import SqlOneTimeLinkSubscriptionRepository
from notification_context.domain.entities import OneTimeLinkSubscription

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def _subscription(expires_at: datetime = T0, **flags) -> OneTimeLinkSubscription:
    return OneTimeLinkSubscription(
        link_id=uuid4(),
        user_id=uuid4(),
        expires_at=expires_at,
        notify_on_read=flags.get("notify_on_read", True),
        notify_on_expiry=flags.get("notify_on_expiry", False),
    )


def test_should_save_and_read_back_a_subscription_with_an_aware_expiry(session):
    repository = SqlOneTimeLinkSubscriptionRepository(session)
    subscription = _subscription(notify_on_read=True, notify_on_expiry=True)

    repository.save(subscription)

    assert repository.get(subscription.link_id) == subscription


def test_given_an_existing_subscription_save_should_replace_it(session):
    repository = SqlOneTimeLinkSubscriptionRepository(session)
    subscription = _subscription(notify_on_read=True, notify_on_expiry=False)
    repository.save(subscription)

    subscription.notify_on_read, subscription.notify_on_expiry = False, True
    repository.save(subscription)

    stored = repository.get(subscription.link_id)
    assert stored is not None
    assert (stored.notify_on_read, stored.notify_on_expiry) == (False, True)


def test_given_an_unknown_link_get_should_return_none(session):
    assert SqlOneTimeLinkSubscriptionRepository(session).get(uuid4()) is None


def test_remove_should_succeed_for_a_single_caller_only(database_engine):
    """Two sessions stand for two concurrent callers (the read notification and the
    sweep, or two replicas): only one of them may get True and send the email."""
    subscription = _subscription()
    with Session(database_engine) as session:
        SqlOneTimeLinkSubscriptionRepository(session).save(subscription)

    with Session(database_engine) as first, Session(database_engine) as second:
        results = [
            SqlOneTimeLinkSubscriptionRepository(first).remove(subscription.link_id),
            SqlOneTimeLinkSubscriptionRepository(second).remove(subscription.link_id),
        ]

    assert results == [True, False]
    with Session(database_engine) as session:
        assert SqlOneTimeLinkSubscriptionRepository(session).get(subscription.link_id) is None


def test_list_expired_should_return_only_expired_ones_oldest_first_and_bounded(session):
    repository = SqlOneTimeLinkSubscriptionRepository(session)
    newest = _subscription(expires_at=T0)
    oldest = _subscription(expires_at=T0 - timedelta(hours=1))
    middle = _subscription(expires_at=T0 - timedelta(minutes=1))
    not_yet = _subscription(expires_at=T0 + timedelta(seconds=1))
    for subscription in (newest, oldest, middle, not_yet):
        repository.save(subscription)

    assert [s.link_id for s in repository.list_expired(T0, limit=10)] == [
        oldest.link_id,
        middle.link_id,
        newest.link_id,
    ]
    assert [s.link_id for s in repository.list_expired(T0, limit=2)] == [oldest.link_id, middle.link_id]
