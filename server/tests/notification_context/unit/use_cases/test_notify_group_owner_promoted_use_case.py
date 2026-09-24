from uuid import UUID

import pytest

from notification_context.application.commands import NotifyGroupOwnerPromotedCommand
from notification_context.application.use_cases import NotifyGroupOwnerPromotedUseCase
from notification_context.domain.value_objects import OwnerPromotionNotification


def test_given_promoted_user_when_notifying_should_send_email_to_new_owner(
    group_ownership_gateway,
    email_gateway,
):
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    added_by_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    group_ownership_gateway.set_owner_promotion_details(
        user_id,
        group_id,
        OwnerPromotionNotification(email="alice@example.com", display_name="Alice", group_name="Development Team"),
    )
    use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    command = NotifyGroupOwnerPromotedCommand(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)

    use_case.execute(command)

    assert len(email_gateway.sent_emails) == 1
    sent = email_gateway.sent_emails[0]
    assert sent["to"] == "alice@example.com"
    assert sent["subject"] == 'You\'re now an owner of "Development Team"'
    assert sent["body"] == 'Hi Alice, you\'ve been made an owner of the group "Development Team".'


def test_given_gateway_returns_no_details_when_notifying_should_not_send_email(
    group_ownership_gateway,
    email_gateway,
):
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    added_by_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    command = NotifyGroupOwnerPromotedCommand(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)

    use_case.execute(command)

    assert email_gateway.sent_emails == []


def test_given_email_delivery_fails_when_notifying_should_swallow_error_and_log(
    group_ownership_gateway,
    email_gateway,
    caplog: pytest.LogCaptureFixture,
):
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    added_by_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    group_ownership_gateway.set_owner_promotion_details(
        user_id,
        group_id,
        OwnerPromotionNotification(email="alice@example.com", display_name="Alice", group_name="Development Team"),
    )
    email_gateway.fail_next_send()
    use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    command = NotifyGroupOwnerPromotedCommand(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)

    with caplog.at_level(
        "ERROR", logger="notification_context.application.use_cases.notify_group_owner_promoted_use_case"
    ):
        use_case.execute(command)  # must not raise

    errors = [rec for rec in caplog.records if rec.levelname == "ERROR" and "alice@example.com" in rec.getMessage()]
    assert errors, "EmailDeliveryError must be logged at ERROR so operators can see the delivery failure"
    assert errors[0].exc_info is not None


def test_given_gateway_lookup_raises_when_notifying_should_swallow_error_and_log(
    group_ownership_gateway,
    email_gateway,
    caplog: pytest.LogCaptureFixture,
):
    user_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    group_id = UUID("223e4567-e89b-12d3-a456-426614174001")
    added_by_user_id = UUID("323e4567-e89b-12d3-a456-426614174002")
    group_ownership_gateway.fail_next_lookup()
    use_case = NotifyGroupOwnerPromotedUseCase(group_ownership_gateway, email_gateway)
    command = NotifyGroupOwnerPromotedCommand(group_id=group_id, user_id=user_id, added_by_user_id=added_by_user_id)

    with caplog.at_level(
        "ERROR", logger="notification_context.application.use_cases.notify_group_owner_promoted_use_case"
    ):
        use_case.execute(command)  # must not raise

    assert email_gateway.sent_emails == []
    errors = [
        rec
        for rec in caplog.records
        if rec.levelname == "ERROR" and "look up owner-promotion details" in rec.getMessage()
    ]
    assert errors, "an unexpected lookup failure must be logged at ERROR, not raised"
    assert errors[0].exc_info is not None
