from notification_context.domain.value_objects import NotificationKind

from .notification_catalog import MissingNotificationTemplateError, NotificationCatalog, NotificationTemplate
from .one_time_link_templates import one_time_link_expired_template, one_time_link_read_template


def default_notification_catalog() -> NotificationCatalog:
    """The catalog the application runs with: one template per NotificationKind."""
    return NotificationCatalog(
        {
            NotificationKind.ONE_TIME_LINK_READ: one_time_link_read_template,
            NotificationKind.ONE_TIME_LINK_EXPIRED: one_time_link_expired_template,
        }
    )


__all__ = [
    "MissingNotificationTemplateError",
    "NotificationCatalog",
    "NotificationTemplate",
    "default_notification_catalog",
]
