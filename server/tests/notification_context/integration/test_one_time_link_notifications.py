from concurrent.futures import Executor, Future
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from identity_access_management_context.adapters.primary.private_api import UserContactInfoApi
from identity_access_management_context.adapters.secondary.sql import SqlUserRepository
from identity_access_management_context.domain.entities import User
from notification_context.adapters.primary.events import OneTimeLinkReadEventSubscriber
from notification_context.adapters.secondary import (
    PrivateApiOneTimeLinkGateway,
    PrivateApiRecipientGateway,
    SqlOneTimeLinkSubscriptionRepository,
)
from notification_context.application.use_cases import NotifyExpiredOneTimeLinksUseCase
from notification_context.domain.entities import OneTimeLinkSubscription
from password_management_context.adapters.primary.private_api import OneTimeLinkInfoApi
from password_management_context.adapters.secondary.sql import SqlOneTimeLinkRepository, SqlPasswordRepository
from password_management_context.domain.entities import OneTimeLink, Password
from password_management_context.domain.events import OneTimeLinkReadEvent
from password_management_context.domain.value_objects import OneTimeLinkLifetime, OneTimeLinkToken
from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher, SmtpEmailGateway
from tests.shared_kernel.fakes import FakeTimeGateway

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
APP_BASE_URL = "https://le-coffre.example.com"


class _InlineExecutor(Executor):
    """Runs submitted work right away, so the test can assert on its outcome."""

    def submit(self, fn, /, *args, **kwargs):
        future: Future = Future()
        future.set_result(fn(*args, **kwargs))
        return future


def _email_gateway(smtpd) -> SmtpEmailGateway:
    return SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")


def _creator(session) -> User:
    user = User(id=uuid4(), username="alice", email="alice@example.com", name="Alice")
    SqlUserRepository(session).save(user)
    return user


def _link(session, creator: User, name: str = "Prod DB") -> OneTimeLink:
    password = Password.create(id=uuid4(), name=name, encrypted_value="enc", login=None, url=None)
    SqlPasswordRepository(session).save(password)
    link = OneTimeLink.create(
        password_id=password.id,
        created_by_user_id=creator.id,
        token=OneTimeLinkToken.generate(),
        lifetime=OneTimeLinkLifetime(seconds=300),
        now=T0,
    )
    SqlOneTimeLinkRepository(session).add(link)
    return link


def _subscribe(session, link: OneTimeLink, **flags) -> None:
    SqlOneTimeLinkSubscriptionRepository(session).save(
        OneTimeLinkSubscription(link_id=link.id, user_id=link.created_by_user_id, expires_at=link.expires_at, **flags)
    )


# ── Private API gateway ──────────────────────────────────────────────


def test_the_gateway_should_report_the_link_as_the_password_context_stores_it(session, session_maker):
    link = _link(session, _creator(session))
    SqlOneTimeLinkRepository(session).consume(link.id, T0 + timedelta(minutes=1))

    details = PrivateApiOneTimeLinkGateway(OneTimeLinkInfoApi(session_maker)).get_link(link.id)

    assert details is not None
    assert details.created_by_user_id == link.created_by_user_id
    assert details.password_name == "Prod DB"
    assert details.expires_at == link.expires_at
    assert details.read_at == T0 + timedelta(minutes=1)
    assert details.revoked_at is None


def test_the_gateway_should_report_an_unknown_link_or_one_whose_password_is_gone_as_none(session, session_maker):
    link = _link(session, _creator(session))
    SqlPasswordRepository(session).delete(link.password_id)
    gateway = PrivateApiOneTimeLinkGateway(OneTimeLinkInfoApi(session_maker))

    assert gateway.get_link(uuid4()) is None
    assert gateway.get_link(link.id) is None


# ── Read notification ────────────────────────────────────────────────


def _publish_read(session_maker, smtpd, link: OneTimeLink) -> None:
    subscriber = OneTimeLinkReadEventSubscriber(
        session_maker=session_maker,
        recipient_gateway=PrivateApiRecipientGateway(UserContactInfoApi(session_maker=session_maker)),
        email_gateway=_email_gateway(smtpd),
        app_base_url=APP_BASE_URL,
        executor=_InlineExecutor(),
    )
    publisher = InMemoryDomainEventPublisher()
    publisher.subscribe(OneTimeLinkReadEvent, subscriber.handle)
    publisher.publish(
        OneTimeLinkReadEvent(
            password_id=link.password_id,
            link_id=link.id,
            created_by_user_id=link.created_by_user_id,
            password_name="Prod DB",
            read_at=T0 + timedelta(minutes=1),
        )
    )


def test_given_a_subscribed_link_when_read_should_email_its_creator_once(session, session_maker, smtpd):
    link = _link(session, _creator(session))
    _subscribe(session, link, notify_on_read=True)

    _publish_read(session_maker, smtpd, link)
    _publish_read(session_maker, smtpd, link)

    assert [m["To"] for m in smtpd.messages] == ["alice@example.com"]
    assert smtpd.messages[0]["Subject"] == "Le Coffre: your one-time link was opened"
    assert SqlOneTimeLinkSubscriptionRepository(session).get(link.id) is None


def test_given_a_link_nobody_follows_when_read_should_send_nothing(session, session_maker, smtpd):
    link = _link(session, _creator(session))

    _publish_read(session_maker, smtpd, link)

    assert smtpd.messages == []


# ── Expiry sweep ─────────────────────────────────────────────────────


def _sweep(session, session_maker, smtpd, now: datetime) -> int:
    return NotifyExpiredOneTimeLinksUseCase(
        SqlOneTimeLinkSubscriptionRepository(session),
        PrivateApiOneTimeLinkGateway(OneTimeLinkInfoApi(session_maker)),
        PrivateApiRecipientGateway(UserContactInfoApi(session_maker=session_maker)),
        _email_gateway(smtpd),
        FakeTimeGateway(fixed_time=now),
        APP_BASE_URL,
    ).execute()


def test_given_links_that_expired_the_sweep_should_email_only_about_the_unused_ones_and_only_once(
    session, session_maker, smtpd
):
    creator = _creator(session)
    unused = _link(session, creator, name="Unused")
    read = _link(session, creator, name="Read")
    revoked = _link(session, creator, name="Revoked")
    for link in (unused, read, revoked):
        _subscribe(session, link, notify_on_expiry=True)
    links = SqlOneTimeLinkRepository(session)
    links.consume(read.id, T0 + timedelta(minutes=1))
    links.revoke(revoked.id, T0 + timedelta(minutes=1))
    after_expiry = unused.expires_at + timedelta(seconds=1)

    assert _sweep(session, session_maker, smtpd, unused.expires_at - timedelta(seconds=1)) == 0
    assert _sweep(session, session_maker, smtpd, after_expiry) == 1
    assert _sweep(session, session_maker, smtpd, after_expiry) == 0

    (message,) = smtpd.messages
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "Le Coffre: your one-time link expired unused"
    assert '"Unused"' in message.get_payload()
    assert SqlOneTimeLinkSubscriptionRepository(session).list_expired(after_expiry, limit=10) == []
