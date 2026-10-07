import logging
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from notification_context.adapters.primary.events import VaultStateChangedEventSubscriber
from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher
from vault_management_context.domain.events import VaultLockedEvent, VaultUnlockedEvent


def _session_maker_that_must_not_be_called():
    def _fail():
        raise AssertionError("session_maker() must not be called: submit() failed before _notify could run")

    return _fail


@pytest.fixture
def shutdown_executor():
    executor = ThreadPoolExecutor(max_workers=1)
    executor.shutdown(wait=True)
    return executor


@pytest.fixture
def publisher(shutdown_executor):
    subscriber = VaultStateChangedEventSubscriber(
        session_maker=_session_maker_that_must_not_be_called(),
        recipient_gateway=None,
        email_gateway=None,
        app_base_url="https://le-coffre.example.com",
        executor=shutdown_executor,
    )
    publisher = InMemoryDomainEventPublisher()
    publisher.subscribe(VaultLockedEvent, subscriber.handle_locked)
    publisher.subscribe(VaultUnlockedEvent, subscriber.handle_unlocked)
    return publisher


# Regression: the lock and unlock use cases publish from inside the request. A
# RuntimeError from submit() (executor already shut down) must not turn an
# otherwise-successful lock or unlock into a 500; the publisher contains it.
@pytest.mark.parametrize(
    "event", [VaultLockedEvent(locked_by_user_id=None), VaultUnlockedEvent()], ids=["lock", "unlock"]
)
def test_given_executor_already_shut_down_publishing_a_vault_event_should_not_raise(publisher, event, caplog):
    other_subscriber = Mock()
    publisher.subscribe(type(event), other_subscriber)

    with caplog.at_level(logging.ERROR):
        publisher.publish(event)

    assert f"failed on {type(event).__name__}" in caplog.text
    other_subscriber.assert_called_once_with(event)
