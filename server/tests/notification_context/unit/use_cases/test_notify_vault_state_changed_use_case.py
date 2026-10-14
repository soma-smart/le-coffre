from uuid import uuid4

import pytest

from notification_context.application.commands import NotifyVaultStateChangedCommand
from notification_context.application.use_cases import NotifyVaultStateChangedUseCase
from notification_context.domain.entities import NotificationPreferences
from notification_context.domain.value_objects import Recipient, VaultStateChange


@pytest.fixture
def use_case(preferences_repository, recipient_gateway, email_gateway, app_base_url):
    return NotifyVaultStateChangedUseCase(preferences_repository, recipient_gateway, email_gateway, app_base_url)


def _user(preferences_repository, recipient_gateway, name, *, on_lock=False, on_unlock=False):
    user_id = uuid4()
    recipient_gateway.add(Recipient(user_id=user_id, email=f"{name.lower()}@example.com", display_name=name))
    preferences_repository.save(
        NotificationPreferences(user_id=user_id, notify_on_vault_lock=on_lock, notify_on_vault_unlock=on_unlock)
    )
    return user_id


def test_given_lock_should_email_only_users_who_opted_in_for_locks(
    use_case, preferences_repository, recipient_gateway, email_gateway
):
    _user(preferences_repository, recipient_gateway, "Alice", on_lock=True)
    _user(preferences_repository, recipient_gateway, "Bob", on_unlock=True)
    _user(preferences_repository, recipient_gateway, "Carol")

    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.LOCKED))

    assert [e["to"] for e in email_gateway.sent_emails] == ["alice@example.com"]


def test_given_unlock_should_email_only_users_who_opted_in_for_unlocks(
    use_case, preferences_repository, recipient_gateway, email_gateway, app_base_url
):
    _user(preferences_repository, recipient_gateway, "Alice", on_lock=True)
    _user(preferences_repository, recipient_gateway, "Bob", on_unlock=True)

    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.UNLOCKED))

    assert len(email_gateway.sent_emails) == 1
    email = email_gateway.sent_emails[0]
    assert email["to"] == "bob@example.com"
    assert email["subject"] == "Le Coffre: the vault was unlocked"
    assert "Hello Bob" in email["body"]
    assert f"{app_base_url}/profile" in email["body"]


def test_given_lock_by_an_admin_should_name_them_and_link_to_the_unlock_page(
    use_case, preferences_repository, recipient_gateway, email_gateway, app_base_url
):
    _user(preferences_repository, recipient_gateway, "Alice", on_lock=True)
    admin_id = uuid4()
    recipient_gateway.add(Recipient(user_id=admin_id, email="admin@example.com", display_name="The Admin"))

    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.LOCKED, locked_by_user_id=admin_id))

    email = email_gateway.sent_emails[0]
    assert email["subject"] == "Le Coffre: the vault was locked"
    assert "locked by The Admin" in email["body"]
    assert f"{app_base_url}/unlock" in email["body"]


def test_given_lock_by_a_server_start_should_say_so(use_case, preferences_repository, recipient_gateway, email_gateway):
    _user(preferences_repository, recipient_gateway, "Alice", on_lock=True)

    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.LOCKED, locked_by_user_id=None))

    assert "because the server restarted" in email_gateway.sent_emails[0]["body"]


def test_given_undeliverable_address_should_still_email_the_others(
    use_case, preferences_repository, recipient_gateway, email_gateway
):
    _user(preferences_repository, recipient_gateway, "Alice", on_unlock=True)
    _user(preferences_repository, recipient_gateway, "Bob", on_unlock=True)
    email_gateway.fail_next_send()

    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.UNLOCKED))

    assert len(email_gateway.sent_emails) == 1


def test_given_deleted_user_still_opted_in_should_skip_them(
    use_case, preferences_repository, recipient_gateway, email_gateway
):
    preferences_repository.save(NotificationPreferences(user_id=uuid4(), notify_on_vault_lock=True))

    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.LOCKED))

    assert email_gateway.sent_emails == []


def test_given_several_recipients_should_use_one_send_bulk_call_not_one_send_per_recipient(
    use_case, preferences_repository, recipient_gateway, email_gateway
):
    # Regression: this used to loop calling send() once per recipient, which meant
    # one SMTP connection per recipient too — a broadcast to hundreds of opted-in
    # users must open one connection for the whole batch instead.
    _user(preferences_repository, recipient_gateway, "Alice", on_lock=True)
    _user(preferences_repository, recipient_gateway, "Bob", on_lock=True)
    _user(preferences_repository, recipient_gateway, "Carol", on_lock=True)

    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.LOCKED))

    assert email_gateway.send_bulk_call_sizes == [3]
    assert email_gateway.send_call_count == 0


def test_given_nobody_opted_in_should_not_even_look_users_up(use_case, recipient_gateway, email_gateway):
    use_case.execute(NotifyVaultStateChangedCommand(change=VaultStateChange.LOCKED))

    assert recipient_gateway.lookups == []
    assert email_gateway.sent_emails == []
