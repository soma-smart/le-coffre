import logging
from concurrent.futures import Executor

from notification_context.application.commands import SendNotificationCommand
from notification_context.application.use_cases import SendNotificationUseCase
from notification_context.domain.value_objects import Notification, NotificationKind
from password_management_context.domain.events import OneTimeLinkExpiredEvent, OneTimeLinkReadEvent

logger = logging.getLogger(__name__)


class OneTimeLinkNotificationEventSubscriber:
    """Primary adapter turning one-time link events into emails to the link's creator.

    The read event is published inside the anonymous consumption request, and sending
    an email can take as long as the relay's connection timeout. The send is therefore
    handed to an executor so that the recipient of the link never waits on it.
    """

    def __init__(self, send_notification_use_case: SendNotificationUseCase, executor: Executor):
        self._send_notification_use_case = send_notification_use_case
        self._executor = executor

    def handle_read(self, event: OneTimeLinkReadEvent) -> None:
        if not event.notify_creator:
            return
        self._submit(
            Notification(
                kind=NotificationKind.ONE_TIME_LINK_READ,
                recipient_user_id=event.created_by_user_id,
                params={"password_name": event.password_name, "read_at": event.read_at.isoformat()},
            )
        )

    def handle_expired(self, event: OneTimeLinkExpiredEvent) -> None:
        # No flag to check here: the sweep only publishes for links that opted in.
        self._submit(
            Notification(
                kind=NotificationKind.ONE_TIME_LINK_EXPIRED,
                recipient_user_id=event.created_by_user_id,
                params={"password_name": event.password_name, "expires_at": event.expires_at.isoformat()},
            )
        )

    def _submit(self, notification: Notification) -> None:
        self._executor.submit(self._send, notification)

    def _send(self, notification: Notification) -> None:
        # Runs on the executor, whose Future nobody reads: without this, a failure
        # would vanish without a trace.
        try:
            self._send_notification_use_case.execute(SendNotificationCommand(notification))
        except Exception:  # noqa: BLE001 - courtesy emails: a failure is logged, never raised into the executor
            logger.error("Failed to send %s notification", notification.kind.value, exc_info=True)
