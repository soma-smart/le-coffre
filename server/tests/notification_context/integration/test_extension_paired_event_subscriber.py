from datetime import UTC, datetime
from uuid import uuid4

from identity_access_management_context.adapters.primary.private_api import UserContactInfoApi
from identity_access_management_context.adapters.secondary.sql import SqlUserRepository
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.events import ExtensionPairedEvent
from notification_context.adapters.primary.events import ExtensionPairedEventSubscriber
from notification_context.adapters.secondary import PrivateApiUserContactGateway
from notification_context.application.use_cases import NotifyExtensionPairedUseCase
from shared_kernel.adapters.secondary import SmtpEmailGateway


def test_given_a_pairing_event_when_handled_should_email_the_owner_end_to_end(session, session_maker, smtpd):
    user_id = uuid4()
    SqlUserRepository(session).save(User(id=user_id, username="alice", email="alice@example.com", name="Alice"))

    user_contact_gateway = PrivateApiUserContactGateway(UserContactInfoApi(session_maker=session_maker))
    email_gateway = SmtpEmailGateway(host=smtpd.hostname, port=smtpd.port, from_address="noreply@le-coffre.local")
    notify_use_case = NotifyExtensionPairedUseCase(
        user_contact_gateway, email_gateway, app_base_url="https://le-coffre.example.com"
    )
    subscriber = ExtensionPairedEventSubscriber(notify_use_case)

    subscriber.handle(
        ExtensionPairedEvent(
            user_id=user_id,
            token_id=uuid4(),
            device_name="Chrome on macOS",
            created_from_ip="203.0.113.5",
            occurred_on=datetime(2026, 9, 29, 14, 5, tzinfo=UTC),
        )
    )

    (message,) = smtpd.messages
    assert message["To"] == "alice@example.com"
    assert message["Subject"] == "A browser extension was connected to your account"
    payload = message.get_payload()
    assert "Chrome on macOS" in payload
    assert "203.0.113.5" in payload
    assert "https://le-coffre.example.com/profile" in payload
