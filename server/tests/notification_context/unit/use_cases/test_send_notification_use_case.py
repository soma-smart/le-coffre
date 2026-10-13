import logging
from enum import Enum
from uuid import uuid4

import pytest

from notification_context.application.commands import SendNotificationCommand
from notification_context.application.templates import (
    MissingNotificationTemplateError,
    NotificationCatalog,
    default_notification_catalog,
)
from notification_context.application.use_cases import SendNotificationUseCase
from notification_context.domain.value_objects import Notification, NotificationKind, Recipient

READ_AT = "2026-01-01T12:34:56+00:00"
EXPIRES_AT = "2026-01-02T08:00:00+00:00"


@pytest.fixture
def creator(recipient_gateway):
    recipient = Recipient(user_id=uuid4(), email="alice@example.com", display_name="Alice")
    recipient_gateway.add(recipient)
    return recipient


@pytest.fixture
def use_case(recipient_gateway, email_gateway, app_base_url):
    return SendNotificationUseCase(recipient_gateway, email_gateway, default_notification_catalog(), app_base_url)


def _read(user_id) -> SendNotificationCommand:
    return SendNotificationCommand(
        Notification(
            kind=NotificationKind.ONE_TIME_LINK_READ,
            recipient_user_id=user_id,
            params={"password_name": "Prod DB", "read_at": READ_AT},
        )
    )


def _expired(user_id) -> SendNotificationCommand:
    return SendNotificationCommand(
        Notification(
            kind=NotificationKind.ONE_TIME_LINK_EXPIRED,
            recipient_user_id=user_id,
            params={"password_name": "Prod DB", "expires_at": EXPIRES_AT},
        )
    )


def test_given_a_read_notification_should_email_the_recipient_with_the_read_template(
    use_case, creator, email_gateway, app_base_url
):
    use_case.execute(_read(creator.user_id))

    (email,) = email_gateway.sent_emails
    assert email["to"] == "alice@example.com"
    assert email["subject"] == "Le Coffre: your one-time link was opened"
    assert "Hello Alice" in email["body"]
    assert 'The one-time link you created for "Prod DB" was opened on 2026-01-01 12:34 UTC.' in email["body"]
    assert "It can no longer be used." in email["body"]
    assert f"{app_base_url}/my-links" in email["body"]
    assert "you asked to be notified" in email["body"]


def test_given_an_expired_notification_should_email_the_recipient_with_the_expired_template(
    use_case, creator, email_gateway, app_base_url
):
    use_case.execute(_expired(creator.user_id))

    (email,) = email_gateway.sent_emails
    assert email["to"] == "alice@example.com"
    assert email["subject"] == "Le Coffre: your one-time link expired unused"
    assert "Hello Alice" in email["body"]
    assert (
        'The one-time link you created for "Prod DB" expired on 2026-01-02 08:00 UTC without being opened.'
        in (email["body"])
    )
    assert f"{app_base_url}/my-links" in email["body"]
    assert "you asked to be notified" in email["body"]


def test_given_a_naive_timestamp_should_be_rendered_as_utc(use_case, creator, email_gateway):
    command = SendNotificationCommand(
        Notification(
            kind=NotificationKind.ONE_TIME_LINK_READ,
            recipient_user_id=creator.user_id,
            params={"password_name": "Prod DB", "read_at": "2026-01-01T12:34:56"},
        )
    )

    use_case.execute(command)

    assert "2026-01-01 12:34 UTC" in email_gateway.sent_emails[0]["body"]


def test_given_an_unknown_recipient_should_log_a_warning_and_send_nothing(use_case, email_gateway, caplog):
    with caplog.at_level(logging.WARNING):
        use_case.execute(_read(uuid4()))

    assert email_gateway.sent_emails == []
    assert "recipient" in caplog.text and "not found" in caplog.text


def test_given_an_smtp_failure_should_log_an_error_and_not_raise(use_case, creator, email_gateway, caplog):
    email_gateway.fail_next_send()

    with caplog.at_level(logging.ERROR):
        use_case.execute(_expired(creator.user_id))

    assert email_gateway.sent_emails == []
    assert "Failed to send ONE_TIME_LINK_EXPIRED notification" in caplog.text


def test_given_a_kind_without_template_should_raise_even_if_the_recipient_is_gone(
    recipient_gateway, email_gateway, app_base_url
):
    use_case = SendNotificationUseCase(recipient_gateway, email_gateway, NotificationCatalog({}), app_base_url)

    with pytest.raises(MissingNotificationTemplateError):
        use_case.execute(_read(uuid4()))

    assert email_gateway.sent_emails == []


@pytest.mark.parametrize("kind", list(NotificationKind))
def test_every_notification_kind_should_have_a_template_in_the_default_catalog(kind):
    default_notification_catalog().template_for(kind)


def test_given_a_new_kind_registered_only_in_the_catalog_should_send_it_without_changing_the_use_case(
    recipient_gateway, email_gateway, app_base_url, creator
):
    """Adding a notification is an enum member, a template and a subscriber: this
    stands a future kind in for the enum member and checks nothing else is needed."""

    class FutureKind(Enum):
        PASSWORD_CHANGED = "PASSWORD_CHANGED"

    catalog = NotificationCatalog(
        {
            FutureKind.PASSWORD_CHANGED: lambda recipient, params, base_url: (
                "Le Coffre: a password changed",
                f"Hello {recipient.display_name}, {params['password_name']} changed: {base_url}",
            )
        }
    )
    use_case = SendNotificationUseCase(recipient_gateway, email_gateway, catalog, app_base_url)

    use_case.execute(
        SendNotificationCommand(
            Notification(
                kind=FutureKind.PASSWORD_CHANGED,  # type: ignore[arg-type]
                recipient_user_id=creator.user_id,
                params={"password_name": "Prod DB"},
            )
        )
    )

    (email,) = email_gateway.sent_emails
    assert email["to"] == "alice@example.com"
    assert email["subject"] == "Le Coffre: a password changed"
    assert email["body"] == f"Hello Alice, Prod DB changed: {app_base_url}"


def test_a_notification_should_not_see_its_params_change_after_creation():
    params = {"password_name": "Prod DB"}
    notification = Notification(NotificationKind.ONE_TIME_LINK_READ, uuid4(), params)

    params["password_name"] = "tampered"

    assert notification.params["password_name"] == "Prod DB"
