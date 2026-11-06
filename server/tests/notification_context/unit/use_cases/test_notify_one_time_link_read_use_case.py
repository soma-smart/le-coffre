from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from notification_context.application.commands import NotifyOneTimeLinkReadCommand
from notification_context.application.use_cases import NotifyOneTimeLinkReadUseCase
from notification_context.domain.entities import OneTimeLinkSubscription
from notification_context.domain.value_objects import Recipient

from ..fakes import FakeOneTimeLinkSubscriptionRepository, FakeRecipientGateway

READ_AT = datetime(2026, 1, 1, 12, 30, tzinfo=UTC)
CREATOR = Recipient(
    user_id=UUID("00000000-0000-0000-0000-0000000000a1"), email="alice@example.com", display_name="Alice"
)
LINK_ID = UUID("00000000-0000-0000-0000-0000000000b1")


def _subscribe(repository: FakeOneTimeLinkSubscriptionRepository, notify_on_read: bool = True) -> None:
    repository.save(
        OneTimeLinkSubscription(
            link_id=LINK_ID,
            user_id=CREATOR.user_id,
            expires_at=READ_AT + timedelta(hours=1),
            notify_on_read=notify_on_read,
            notify_on_expiry=True,
        )
    )


COMMAND = NotifyOneTimeLinkReadCommand(link_id=LINK_ID, password_name="Prod DB", read_at=READ_AT)


@pytest.fixture
def use_case(subscription_repository, recipient_gateway, email_gateway, app_base_url):
    recipient_gateway.add(CREATOR)
    return NotifyOneTimeLinkReadUseCase(subscription_repository, recipient_gateway, email_gateway, app_base_url)


def test_given_a_creator_who_asked_should_email_them_without_the_token_or_secret(
    use_case, subscription_repository, email_gateway
):
    _subscribe(subscription_repository)

    use_case.execute(COMMAND)

    (email,) = email_gateway.sent_emails
    assert email["to"] == "alice@example.com"
    assert email["subject"] == "Le Coffre: your one-time link was opened"
    assert "Hello Alice" in email["body"]
    assert 'for "Prod DB" was opened on 2026-01-01 12:30 UTC' in email["body"]
    assert "https://le-coffre.example.com/my-links" in email["body"]


def test_given_a_read_should_remove_the_subscription_so_the_expiry_sweep_never_sees_it(
    use_case, subscription_repository
):
    _subscribe(subscription_repository)

    use_case.execute(COMMAND)

    assert subscription_repository.get(LINK_ID) is None


def test_given_a_subscription_to_the_expiry_only_should_remove_it_and_send_nothing(
    use_case, subscription_repository, email_gateway
):
    _subscribe(subscription_repository, notify_on_read=False)

    use_case.execute(COMMAND)

    assert email_gateway.sent_emails == []
    assert subscription_repository.get(LINK_ID) is None


def test_given_no_subscription_should_send_nothing(use_case, email_gateway, recipient_gateway):
    use_case.execute(COMMAND)

    assert email_gateway.sent_emails == []
    assert recipient_gateway.lookups == []


class _RemovedByAnotherCaller(FakeOneTimeLinkSubscriptionRepository):
    """The subscription is still there when read, but someone else deletes it first."""

    def remove(self, link_id: UUID) -> bool:
        super().remove(link_id)
        return False


def test_given_a_subscription_removed_meanwhile_should_send_nothing(recipient_gateway, email_gateway, app_base_url):
    """The expiry sweep (or another replica) settled the subscription between our
    read and our removal: it is the one that sends, not us."""
    repository = _RemovedByAnotherCaller()
    _subscribe(repository)
    recipient_gateway.add(CREATOR)

    NotifyOneTimeLinkReadUseCase(repository, recipient_gateway, email_gateway, app_base_url).execute(COMMAND)

    assert email_gateway.sent_emails == []


def test_given_a_creator_who_no_longer_exists_should_send_nothing(
    subscription_repository, email_gateway, app_base_url, caplog
):
    _subscribe(subscription_repository)

    NotifyOneTimeLinkReadUseCase(subscription_repository, FakeRecipientGateway(), email_gateway, app_base_url).execute(
        COMMAND
    )

    assert email_gateway.sent_emails == []
    assert "not found" in caplog.text


def test_given_a_failing_relay_should_log_and_not_raise(use_case, subscription_repository, email_gateway, caplog):
    _subscribe(subscription_repository)
    email_gateway.fail_next_send()

    use_case.execute(COMMAND)

    assert email_gateway.sent_emails == []
    assert "Failed to send the one-time link opened email" in caplog.text
