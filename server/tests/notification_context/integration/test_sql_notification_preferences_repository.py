from uuid import uuid4

from notification_context.adapters.secondary.sql import SqlNotificationPreferencesRepository
from notification_context.domain.entities import NotificationPreferences


def test_given_no_row_should_return_none(session):
    assert SqlNotificationPreferencesRepository(session).get(uuid4()) is None


def test_save_should_insert_then_replace(session):
    repository = SqlNotificationPreferencesRepository(session)
    user_id = uuid4()

    repository.save(NotificationPreferences(user_id=user_id, notify_on_vault_lock=True))
    repository.save(NotificationPreferences(user_id=user_id, notify_on_vault_unlock=True))

    assert repository.get(user_id) == NotificationPreferences(
        user_id=user_id, notify_on_vault_lock=False, notify_on_vault_unlock=True
    )


def test_should_list_only_users_opted_in_for_the_given_change(session):
    repository = SqlNotificationPreferencesRepository(session)
    on_lock, on_unlock, on_both, on_none = uuid4(), uuid4(), uuid4(), uuid4()
    repository.save(NotificationPreferences(user_id=on_lock, notify_on_vault_lock=True))
    repository.save(NotificationPreferences(user_id=on_unlock, notify_on_vault_unlock=True))
    repository.save(NotificationPreferences(user_id=on_both, notify_on_vault_lock=True, notify_on_vault_unlock=True))
    repository.save(NotificationPreferences(user_id=on_none))

    assert set(repository.list_user_ids_to_notify_on_lock()) == {on_lock, on_both}
    assert set(repository.list_user_ids_to_notify_on_unlock()) == {on_unlock, on_both}


def test_delete_should_remove_only_that_users_preferences(session):
    repository = SqlNotificationPreferencesRepository(session)
    deleted, kept = uuid4(), uuid4()
    repository.save(NotificationPreferences(user_id=deleted, notify_on_vault_lock=True))
    repository.save(NotificationPreferences(user_id=kept, notify_on_vault_lock=True))

    repository.delete(deleted)

    assert repository.get(deleted) is None
    assert repository.list_user_ids_to_notify_on_lock() == [kept]


def test_delete_should_ignore_a_user_without_preferences(session):
    SqlNotificationPreferencesRepository(session).delete(uuid4())
