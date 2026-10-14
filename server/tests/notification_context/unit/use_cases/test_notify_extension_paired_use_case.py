"""The email that catches an approval the user should not have given."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from notification_context.application.commands import NotifyExtensionPairedCommand
from notification_context.application.use_cases import NotifyExtensionPairedUseCase
from notification_context.domain.value_objects import UserContact

USER_ID = UUID("123e4567-e89b-12d3-a456-426614174000")
PAIRED_AT = datetime(2026, 9, 29, 14, 5, tzinfo=UTC)


def _command(**overrides):
    values = {
        "user_id": USER_ID,
        "device_name": "Chrome on macOS",
        "created_from_ip": "203.0.113.5",
        "paired_at": PAIRED_AT,
    }
    values.update(overrides)
    return NotifyExtensionPairedCommand(**values)


def test_should_email_the_owner_naming_the_device_and_the_origin(user_contact_gateway, email_gateway, app_base_url):
    user_contact_gateway.set_contact(USER_ID, UserContact(email="alice@example.com", display_name="Alice"))
    use_case = NotifyExtensionPairedUseCase(user_contact_gateway, email_gateway, app_base_url)

    use_case.execute(_command())

    (sent,) = email_gateway.sent_emails
    assert sent["to"] == "alice@example.com"
    assert sent["subject"] == "A browser extension was connected to your account"
    assert sent["body"] == (
        "Hello Alice,\n\n"
        "A browser extension was connected to your Le Coffre account on 2026-09-29 at 14:05 from 203.0.113.5.\n"
        'Device, as reported by the extension: "Chrome on macOS"\n\n'
        "It can read the passwords you can already read, nothing more, until it is disconnected or expires.\n\n"
        "If this was not you, disconnect it now from your profile and change your password:\n"
        "https://le-coffre.example.com/profile"
    )


def test_should_omit_the_origin_when_the_address_is_unknown(user_contact_gateway, email_gateway, app_base_url):
    user_contact_gateway.set_contact(USER_ID, UserContact(email="alice@example.com", display_name="Alice"))
    use_case = NotifyExtensionPairedUseCase(user_contact_gateway, email_gateway, app_base_url)

    use_case.execute(_command(created_from_ip=None))

    assert " from " not in email_gateway.sent_emails[0]["body"].splitlines()[2]


def test_should_send_nothing_when_the_user_is_unknown(user_contact_gateway, email_gateway, app_base_url):
    use_case = NotifyExtensionPairedUseCase(user_contact_gateway, email_gateway, app_base_url)

    use_case.execute(_command())

    assert email_gateway.sent_emails == []


def test_should_swallow_and_log_when_the_lookup_fails(
    user_contact_gateway, email_gateway, app_base_url, caplog: pytest.LogCaptureFixture
):
    # The credential is already issued; a lookup failure must not turn a
    # completed pairing into an error.
    user_contact_gateway.fail_next_lookup()
    use_case = NotifyExtensionPairedUseCase(user_contact_gateway, email_gateway, app_base_url)

    with caplog.at_level("ERROR"):
        use_case.execute(_command())

    assert email_gateway.sent_emails == []
    assert any(record.levelname == "ERROR" and str(USER_ID) in record.getMessage() for record in caplog.records)


def test_should_swallow_and_log_when_delivery_fails(
    user_contact_gateway, email_gateway, app_base_url, caplog: pytest.LogCaptureFixture
):
    user_contact_gateway.set_contact(USER_ID, UserContact(email="alice@example.com", display_name="Alice"))
    email_gateway.fail_next_send()
    use_case = NotifyExtensionPairedUseCase(user_contact_gateway, email_gateway, app_base_url)

    with caplog.at_level("ERROR"):
        use_case.execute(_command())

    errors = [r for r in caplog.records if r.levelname == "ERROR" and "alice@example.com" in r.getMessage()]
    assert errors and errors[0].exc_info is not None
