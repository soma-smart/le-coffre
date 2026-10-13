import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from notification_context.adapters.primary.events import OneTimeLinkNotificationEventSubscriber
from notification_context.domain.value_objects import Notification, NotificationKind
from password_management_context.domain.events import OneTimeLinkExpiredEvent, OneTimeLinkReadEvent
from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class _RecordingExecutor:
    """Queues submitted work instead of running it, to prove the subscriber never runs it inline."""

    def __init__(self):
        self.queued = []

    def submit(self, fn, /, *args, **kwargs):
        self.queued.append((fn, args, kwargs))

    def run_all(self):
        for fn, args, kwargs in self.queued:
            fn(*args, **kwargs)
        self.queued.clear()


@pytest.fixture
def use_case():
    return Mock()


@pytest.fixture
def executor():
    return _RecordingExecutor()


@pytest.fixture
def subscriber(use_case, executor):
    return OneTimeLinkNotificationEventSubscriber(use_case, executor)


def _read_event(notify_creator: bool, creator_id=None) -> OneTimeLinkReadEvent:
    return OneTimeLinkReadEvent(
        password_id=uuid4(),
        link_id=uuid4(),
        created_by_user_id=creator_id or uuid4(),
        notify_creator=notify_creator,
        password_name="Prod DB",
        read_at=NOW,
    )


def _expired_event(creator_id=None) -> OneTimeLinkExpiredEvent:
    return OneTimeLinkExpiredEvent(
        password_id=uuid4(),
        link_id=uuid4(),
        created_by_user_id=creator_id or uuid4(),
        password_name="Prod DB",
        expires_at=NOW,
    )


def test_given_a_read_event_with_notify_creator_should_queue_a_read_notification_without_sending_it_inline(
    subscriber, use_case, executor
):
    creator_id = uuid4()

    subscriber.handle_read(_read_event(notify_creator=True, creator_id=creator_id))

    use_case.execute.assert_not_called()
    assert len(executor.queued) == 1

    executor.run_all()
    (command,) = use_case.execute.call_args.args
    assert command.notification == Notification(
        kind=NotificationKind.ONE_TIME_LINK_READ,
        recipient_user_id=creator_id,
        params={"password_name": "Prod DB", "read_at": NOW.isoformat()},
    )


def test_given_a_read_event_without_notify_creator_should_do_nothing(subscriber, use_case, executor):
    subscriber.handle_read(_read_event(notify_creator=False))

    assert executor.queued == []
    use_case.execute.assert_not_called()


def test_given_an_expired_event_should_queue_an_expired_notification(subscriber, use_case, executor):
    creator_id = uuid4()

    subscriber.handle_expired(_expired_event(creator_id=creator_id))
    executor.run_all()

    (command,) = use_case.execute.call_args.args
    assert command.notification == Notification(
        kind=NotificationKind.ONE_TIME_LINK_EXPIRED,
        recipient_user_id=creator_id,
        params={"password_name": "Prod DB", "expires_at": NOW.isoformat()},
    )


def test_given_the_use_case_fails_on_the_executor_should_log_and_not_raise(subscriber, use_case, executor, caplog):
    use_case.execute.side_effect = RuntimeError("boom")
    subscriber.handle_expired(_expired_event())

    with caplog.at_level(logging.ERROR):
        executor.run_all()

    assert "Failed to send ONE_TIME_LINK_EXPIRED notification" in caplog.text
    assert "boom" in caplog.text


@pytest.mark.parametrize("event", [_read_event(True), _expired_event()], ids=["read", "expired"])
def test_given_executor_already_shut_down_publishing_should_not_raise(use_case, event, caplog):
    # Same regression as the vault subscriber: submit() raising must be contained by the
    # publisher, since the read event is published from inside the anonymous request.
    shut_down = ThreadPoolExecutor(max_workers=1)
    shut_down.shutdown(wait=True)
    subscriber = OneTimeLinkNotificationEventSubscriber(use_case, shut_down)
    publisher = InMemoryDomainEventPublisher()
    publisher.subscribe(OneTimeLinkReadEvent, subscriber.handle_read)
    publisher.subscribe(OneTimeLinkExpiredEvent, subscriber.handle_expired)

    with caplog.at_level(logging.ERROR):
        publisher.publish(event)

    assert f"failed on {type(event).__name__}" in caplog.text
