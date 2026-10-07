from typing import Callable

from sqlmodel import Session

from identity_access_management_context.domain.events import UserDeletedEvent
from notification_context.adapters.secondary.sql import SqlNotificationPreferencesRepository
from notification_context.application.commands import DeleteNotificationPreferencesForDeletedUserCommand
from notification_context.application.use_cases import DeleteNotificationPreferencesForDeletedUserUseCase


class UserDeletedEventSubscriber:
    """Primary adapter subscribing to UserDeletedEvent to drop the deleted user's preferences.

    The table has no foreign key to User (bounded contexts do not share tables), so
    nothing else removes the row.
    """

    def __init__(self, session_maker: Callable[[], Session]):
        self._session_maker = session_maker

    def handle(self, event: UserDeletedEvent) -> None:
        with self._session_maker() as session:
            DeleteNotificationPreferencesForDeletedUserUseCase(SqlNotificationPreferencesRepository(session)).execute(
                DeleteNotificationPreferencesForDeletedUserCommand(user_id=event.user_id)
            )
