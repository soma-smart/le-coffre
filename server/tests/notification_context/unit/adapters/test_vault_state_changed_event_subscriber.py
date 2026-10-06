import logging
from concurrent.futures import ThreadPoolExecutor

import pytest

from notification_context.adapters.primary.events import VaultStateChangedEventSubscriber
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
def subscriber(shutdown_executor):
    return VaultStateChangedEventSubscriber(
        session_maker=_session_maker_that_must_not_be_called(),
        recipient_gateway=None,
        email_gateway=None,
        app_base_url="https://le-coffre.example.com",
        executor=shutdown_executor,
    )


def test_given_executor_already_shut_down_handling_a_lock_should_not_raise(subscriber, caplog):
    # Regression: publish() calls this handler synchronously, with no safety net,
    # from inside LockVaultUseCase — after the decrypted key was already cleared but
    # before the audit event is persisted. A RuntimeError from submit() escaping here
    # would surface as a 500 on an otherwise-successful lock and skip the audit event.
    with caplog.at_level(logging.ERROR):
        subscriber.handle_locked(VaultLockedEvent(locked_by_user_id=None))

    assert "Failed to submit vault LOCKED notifications" in caplog.text


def test_given_executor_already_shut_down_handling_an_unlock_should_not_raise(subscriber, caplog):
    with caplog.at_level(logging.ERROR):
        subscriber.handle_unlocked(VaultUnlockedEvent())

    assert "Failed to submit vault UNLOCKED notifications" in caplog.text
