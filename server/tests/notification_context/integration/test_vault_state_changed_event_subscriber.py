from concurrent.futures import Executor, Future
from uuid import uuid4

from identity_access_management_context.adapters.primary.private_api import UserContactInfoApi
from identity_access_management_context.adapters.secondary.sql import SqlUserRepository
from identity_access_management_context.domain.entities import User
from notification_context.adapters.primary.events import VaultStateChangedEventSubscriber
from notification_context.adapters.secondary import (
    PrivateApiRecipientGateway,
    SqlNotificationPreferencesRepository,
)
from notification_context.domain.entities import NotificationPreferences
from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher, SmtpEmailGateway
from vault_management_context.domain.events import VaultLockedEvent, VaultUnlockedEvent


class _InlineExecutor(Executor):
    """Runs submitted work right away, so the test can assert on its outcome."""

    def submit(self, fn, /, *args, **kwargs):
        future: Future = Future()
        future.set_result(fn(*args, **kwargs))
        return future


def _subscriber(session_maker, smtpd):
    return VaultStateChangedEventSubscriber(
        session_maker=session_maker,
        recipient_gateway=PrivateApiRecipientGateway(UserContactInfoApi(session_maker=session_maker)),
        email_gateway=SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local"),
        app_base_url="https://le-coffre.example.com",
        executor=_InlineExecutor(),
    )


def _user(session, name, **preferences):
    user_id = uuid4()
    SqlUserRepository(session).save(
        User(id=user_id, username=name.lower(), email=f"{name.lower()}@example.com", name=name)
    )
    SqlNotificationPreferencesRepository(session).save(NotificationPreferences(user_id=user_id, **preferences))
    return user_id


def test_given_vault_events_should_email_opted_in_users_once_per_event_end_to_end(session, session_maker, smtpd):
    admin_id = _user(session, "Admin")
    _user(session, "Alice", notify_on_vault_lock=True)
    _user(session, "Bob", notify_on_vault_unlock=True)
    publisher = InMemoryDomainEventPublisher()
    subscriber = _subscriber(session_maker, smtpd)
    publisher.subscribe(VaultLockedEvent, subscriber.handle_locked)
    publisher.subscribe(VaultUnlockedEvent, subscriber.handle_unlocked)

    publisher.publish(VaultLockedEvent(locked_by_user_id=admin_id))

    assert [m["To"] for m in smtpd.messages] == ["alice@example.com"]
    assert smtpd.messages[0]["Subject"] == "Le Coffre: the vault was locked"
    assert "locked by Admin" in smtpd.messages[0].get_payload()

    publisher.publish(VaultUnlockedEvent())

    assert [m["To"] for m in smtpd.messages] == ["alice@example.com", "bob@example.com"]
    assert smtpd.messages[1]["Subject"] == "Le Coffre: the vault was unlocked"
