from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from notification_context.application.use_cases import NotifyExpiredOneTimeLinksUseCase
from notification_context.domain.entities import OneTimeLinkSubscription
from notification_context.domain.value_objects import OneTimeLinkDetails, Recipient
from tests.shared_kernel.fakes import FakeTimeGateway

from ..fakes import FakeOneTimeLinkGateway, FakeOneTimeLinkSubscriptionRepository, FakeRecipientGateway

EXPIRES_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
AFTER_EXPIRY = EXPIRES_AT + timedelta(minutes=1)
CREATOR = Recipient(
    user_id=UUID("00000000-0000-0000-0000-0000000000a1"), email="alice@example.com", display_name="Alice"
)


def _follow(
    repository: FakeOneTimeLinkSubscriptionRepository,
    gateway: FakeOneTimeLinkGateway,
    notify_on_read: bool = False,
    notify_on_expiry: bool = True,
    expires_at: datetime = EXPIRES_AT,
    read_at: datetime | None = None,
    revoked_at: datetime | None = None,
    in_password_context: bool = True,
) -> UUID:
    link_id = uuid4()
    repository.save(
        OneTimeLinkSubscription(
            link_id=link_id,
            user_id=CREATOR.user_id,
            expires_at=expires_at,
            notify_on_read=notify_on_read,
            notify_on_expiry=notify_on_expiry,
        )
    )
    if in_password_context:
        gateway.add(
            OneTimeLinkDetails(
                link_id=link_id,
                created_by_user_id=CREATOR.user_id,
                password_name="Prod DB",
                expires_at=expires_at,
                read_at=read_at,
                revoked_at=revoked_at,
            )
        )
    return link_id


@pytest.fixture
def time_gateway():
    return FakeTimeGateway(fixed_time=AFTER_EXPIRY)


@pytest.fixture
def use_case(
    subscription_repository, one_time_link_gateway, recipient_gateway, email_gateway, time_gateway, app_base_url
):
    recipient_gateway.add(CREATOR)
    return NotifyExpiredOneTimeLinksUseCase(
        subscription_repository, one_time_link_gateway, recipient_gateway, email_gateway, time_gateway, app_base_url
    )


def test_given_a_link_that_expired_unused_should_email_its_creator_once(
    use_case, subscription_repository, one_time_link_gateway, email_gateway
):
    link_id = _follow(subscription_repository, one_time_link_gateway)

    assert use_case.execute() == 1
    assert use_case.execute() == 0

    (email,) = email_gateway.sent_emails
    assert email["to"] == "alice@example.com"
    assert email["subject"] == "Le Coffre: your one-time link expired unused"
    assert 'for "Prod DB" expired on 2026-01-01 12:00 UTC without being opened' in email["body"]
    assert "https://le-coffre.example.com/my-links" in email["body"]
    assert subscription_repository.get(link_id) is None


def test_given_a_link_not_expired_yet_should_leave_it_alone(
    use_case, subscription_repository, one_time_link_gateway, email_gateway
):
    link_id = _follow(subscription_repository, one_time_link_gateway, expires_at=AFTER_EXPIRY + timedelta(seconds=1))

    assert use_case.execute() == 0

    assert email_gateway.sent_emails == []
    assert subscription_repository.get(link_id) is not None


@pytest.mark.parametrize(
    "link_state",
    [
        {"revoked_at": EXPIRES_AT - timedelta(minutes=5)},
        {"in_password_context": False},
    ],
    ids=["revoked", "gone with its password"],
)
def test_given_a_link_there_is_nothing_to_say_about_should_settle_it_silently(
    link_state, use_case, subscription_repository, one_time_link_gateway, email_gateway
):
    link_id = _follow(subscription_repository, one_time_link_gateway, **link_state)

    assert use_case.execute() == 0

    assert email_gateway.sent_emails == []
    assert subscription_repository.get(link_id) is None


def test_given_a_subscription_to_the_read_only_and_a_link_expired_unused_should_settle_it_silently(
    use_case, subscription_repository, one_time_link_gateway, email_gateway
):
    link_id = _follow(subscription_repository, one_time_link_gateway, notify_on_read=True, notify_on_expiry=False)

    assert use_case.execute() == 0

    assert email_gateway.sent_emails == []
    assert subscription_repository.get(link_id) is None


def test_given_a_link_read_whose_read_notification_is_still_pending_should_send_the_opened_email(
    use_case, subscription_repository, one_time_link_gateway, email_gateway
):
    """Read just before expiring: the sweep got to the subscription first, so it is
    the one that tells the creator, and it tells what really happened."""
    _follow(
        subscription_repository,
        one_time_link_gateway,
        notify_on_read=True,
        notify_on_expiry=True,
        read_at=EXPIRES_AT - timedelta(seconds=1),
    )

    assert use_case.execute() == 1

    (email,) = email_gateway.sent_emails
    assert email["subject"] == "Le Coffre: your one-time link was opened"


def test_given_a_link_read_by_someone_who_only_asked_about_expiry_should_send_nothing(
    use_case, subscription_repository, one_time_link_gateway, email_gateway
):
    _follow(subscription_repository, one_time_link_gateway, read_at=EXPIRES_AT - timedelta(seconds=1))

    assert use_case.execute() == 0
    assert email_gateway.sent_emails == []


def test_given_a_subscription_settled_meanwhile_should_send_nothing(
    one_time_link_gateway, recipient_gateway, email_gateway, time_gateway, app_base_url
):
    """Another replica, or the read notification, removed it first."""

    class RemovedByAnotherCaller(FakeOneTimeLinkSubscriptionRepository):
        def remove(self, link_id: UUID) -> bool:
            super().remove(link_id)
            return False

    repository = RemovedByAnotherCaller()
    _follow(repository, one_time_link_gateway)
    recipient_gateway.add(CREATOR)

    sent = NotifyExpiredOneTimeLinksUseCase(
        repository, one_time_link_gateway, recipient_gateway, email_gateway, time_gateway, app_base_url
    ).execute()

    assert sent == 0
    assert email_gateway.sent_emails == []


def test_given_a_failing_link_lookup_should_skip_that_link_and_keep_it_for_the_next_pass(
    use_case, subscription_repository, one_time_link_gateway, email_gateway, caplog
):
    failing = _follow(subscription_repository, one_time_link_gateway)
    _follow(subscription_repository, one_time_link_gateway, expires_at=EXPIRES_AT + timedelta(seconds=1))
    one_time_link_gateway.fail_for(failing)

    assert use_case.execute() == 1

    assert len(email_gateway.sent_emails) == 1
    assert subscription_repository.get(failing) is not None
    assert "Failed to look up one-time link" in caplog.text


def test_given_several_expired_links_should_send_them_in_one_bulk_call(
    use_case, subscription_repository, one_time_link_gateway, email_gateway, recipient_gateway
):
    for _ in range(3):
        _follow(subscription_repository, one_time_link_gateway)

    assert use_case.execute() == 3

    assert email_gateway.send_bulk_call_sizes == [3]
    assert recipient_gateway.lookups == [[CREATOR.user_id]]


def test_given_more_expired_links_than_the_batch_should_handle_the_oldest_first(
    subscription_repository, one_time_link_gateway, recipient_gateway, email_gateway, time_gateway, app_base_url
):
    newest = _follow(subscription_repository, one_time_link_gateway, expires_at=EXPIRES_AT)
    oldest = _follow(subscription_repository, one_time_link_gateway, expires_at=EXPIRES_AT - timedelta(minutes=1))
    recipient_gateway.add(CREATOR)
    use_case = NotifyExpiredOneTimeLinksUseCase(
        subscription_repository,
        one_time_link_gateway,
        recipient_gateway,
        email_gateway,
        time_gateway,
        app_base_url,
        batch_size=1,
    )

    assert use_case.execute() == 1

    assert subscription_repository.get(oldest) is None
    assert subscription_repository.get(newest) is not None


def test_given_a_creator_who_no_longer_exists_should_settle_without_sending(
    subscription_repository, one_time_link_gateway, email_gateway, time_gateway, app_base_url
):
    link_id = _follow(subscription_repository, one_time_link_gateway)

    sent = NotifyExpiredOneTimeLinksUseCase(
        subscription_repository,
        one_time_link_gateway,
        FakeRecipientGateway(),
        email_gateway,
        time_gateway,
        app_base_url,
    ).execute()

    assert sent == 0
    assert email_gateway.sent_emails == []
    assert subscription_repository.get(link_id) is None


def test_given_one_undeliverable_email_should_still_send_the_others(
    use_case, subscription_repository, one_time_link_gateway, email_gateway, caplog
):
    _follow(subscription_repository, one_time_link_gateway)
    _follow(subscription_repository, one_time_link_gateway)
    email_gateway.fail_next_send()

    assert use_case.execute() == 1

    assert len(email_gateway.sent_emails) == 1
    assert "Failed to send a one-time link email to alice@example.com" in caplog.text
