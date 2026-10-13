from dataclasses import dataclass

from notification_context.domain.value_objects import Notification


@dataclass(frozen=True)
class SendNotificationCommand:
    notification: Notification
