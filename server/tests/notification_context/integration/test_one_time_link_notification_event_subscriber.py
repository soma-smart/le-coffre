import logging
from concurrent.futures import Executor, Future
from datetime import UTC, datetime
from uuid import uuid4

from identity_access_management_context.adapters.primary.private_api import UserContactInfoApi
from identity_access_management_context.adapters.secondary.sql import SqlUserRepository
from identity_access_management_context.domain.entities import User
from notification_context.adapters.primary.events import OneTimeLinkNotificationEventSubscriber
from notification_context.adapters.secondary import PrivateApiRecipientGateway
from notification_context.application.templates import default_notification_catalog
from notification_context.application.use_cases import SendNotificationUseCase
from password_management_context.domain.events import OneTimeLinkExpiredEvent, OneTimeLinkReadEvent
from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher, SmtpEmailGateway

BASE_URL = "https://le-coffre.example.com"
NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class _InlineExecutor(Executor):
    """Runs submitted work right away, so the test can assert on its outcome."""

    def submit(self, fn, /, *args, **kwargs):
        future: Future = Future()
        future.set_result(fn(*args, **kwargs))
        return future


def _publisher(session_maker, host, port) -> InMemoryDomainEventPublisher:
    use_case = SendNotificationUseCase(
        recipient_gateway=PrivateApiRecipientGateway(UserContactInfoApi(session_maker=session_maker)),
        email_gateway=SmtpEmailGateway(host=host, port=port, from_address="noreply@le-coffre.local"),
        catalog=default_notification_catalog(),
        app_base_url=BASE_URL,
    )
    subscriber = OneTimeLinkNotificationEventSubscriber(use_case, _InlineExecutor())
    publisher = InMemoryDomainEventPublisher()
    publisher.subscribe(OneTimeLinkReadEvent, subscriber.handle_read)
    publisher.subscribe(OneTimeLinkExpiredEvent, subscriber.handle_expired)
    return publisher


def _user(session, name):
    user_id = uuid4()
    SqlUserRepository(session).save(
        User(id=user_id, username=name.lower(), email=f"{name.lower()}@example.com", name=name)
    )
    return user_id


def _read_event(creator_id, notify_creator=True) -> OneTimeLinkReadEvent:
    return OneTimeLinkReadEvent(
        password_id=uuid4(),
        link_id=uuid4(),
        created_by_user_id=creator_id,
        notify_creator=notify_creator,
        password_name="Prod DB",
        read_at=NOW,
    )


def _expired_event(creator_id) -> OneTimeLinkExpiredEvent:
    return OneTimeLinkExpiredEvent(
        password_id=uuid4(),
        link_id=uuid4(),
        created_by_user_id=creator_id,
        password_name="Prod DB",
        expires_at=NOW,
    )


def test_given_a_read_event_should_email_the_link_creator_end_to_end(session, session_maker, smtpd):
    creator_id = _user(session, "Alice")
    _user(session, "Bob")
    publisher = _publisher(session_maker, smtpd.hostname, smtpd.port)

    publisher.publish(_read_event(creator_id))

    (message,) = smtpd.messages
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "Le Coffre: your one-time link was opened"
    payload = message.get_payload(decode=True).decode()
    assert "Hello Alice" in payload
    assert 'created for "Prod DB" was opened on 2026-01-01 12:00 UTC' in payload
    assert f"{BASE_URL}/my-links" in payload


def test_given_a_read_event_without_notify_creator_should_send_no_email(session, session_maker, smtpd):
    creator_id = _user(session, "Alice")
    publisher = _publisher(session_maker, smtpd.hostname, smtpd.port)

    publisher.publish(_read_event(creator_id, notify_creator=False))

    assert smtpd.messages == []


def test_given_an_expired_event_should_email_the_link_creator_end_to_end(session, session_maker, smtpd):
    creator_id = _user(session, "Alice")
    publisher = _publisher(session_maker, smtpd.hostname, smtpd.port)

    publisher.publish(_expired_event(creator_id))

    (message,) = smtpd.messages
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "Le Coffre: your one-time link expired unused"
    assert (
        'created for "Prod DB" expired on 2026-01-01 12:00 UTC without being opened'
        in message.get_payload(decode=True).decode()
    )


def test_given_a_deleted_creator_should_send_nothing_and_not_raise(session, session_maker, smtpd, caplog):
    publisher = _publisher(session_maker, smtpd.hostname, smtpd.port)

    with caplog.at_level(logging.WARNING):
        publisher.publish(_read_event(uuid4()))

    assert smtpd.messages == []
    assert "not found" in caplog.text


def test_given_an_unreachable_smtp_relay_should_log_and_not_raise(session, session_maker, caplog):
    creator_id = _user(session, "Alice")
    # Port 1 on localhost: nothing listens, the connection is refused at once.
    publisher = _publisher(session_maker, "127.0.0.1", 1)

    with caplog.at_level(logging.ERROR):
        publisher.publish(_expired_event(creator_id))

    assert "Failed to send ONE_TIME_LINK_EXPIRED notification" in caplog.text
