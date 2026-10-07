from uuid import uuid4

from identity_access_management_context.domain.events import UserDeletedEvent
from notification_context.adapters.primary.events import UserDeletedEventSubscriber
from notification_context.adapters.secondary import SqlNotificationPreferencesRepository
from notification_context.domain.entities import NotificationPreferences
from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher


def test_given_user_deleted_should_remove_their_preferences_row(session, session_maker):
    repository = SqlNotificationPreferencesRepository(session)
    deleted, kept = uuid4(), uuid4()
    repository.save(NotificationPreferences(user_id=deleted, notify_on_vault_lock=True))
    repository.save(NotificationPreferences(user_id=kept, notify_on_vault_unlock=True))
    publisher = InMemoryDomainEventPublisher()
    publisher.subscribe(UserDeletedEvent, UserDeletedEventSubscriber(session_maker).handle)

    publisher.publish(UserDeletedEvent(user_id=deleted, deleted_by_user_id=uuid4(), personal_group_id=None))

    session.expire_all()
    assert repository.get(deleted) is None
    assert repository.get(kept) is not None
