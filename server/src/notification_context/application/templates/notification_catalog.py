from typing import Callable, Mapping

from notification_context.domain.value_objects import NotificationKind, Recipient

# How one kind of notification is written: (recipient, params, app_base_url) -> (subject, body).
NotificationTemplate = Callable[[Recipient, Mapping[str, str], str], tuple[str, str]]


class MissingNotificationTemplateError(Exception):
    """A NotificationKind has no template: a programming error, never a runtime condition."""

    def __init__(self, kind: NotificationKind):
        super().__init__(f"No notification template registered for {kind.name}")
        self.kind = kind


class NotificationCatalog:
    """The one place that maps each NotificationKind to the way its email is written.

    Extending it is adding an entry; the use case that sends notifications does not
    know any kind in particular.
    """

    def __init__(self, templates: Mapping[NotificationKind, NotificationTemplate]):
        self._templates = dict(templates)

    def render(
        self, kind: NotificationKind, recipient: Recipient, params: Mapping[str, str], app_base_url: str
    ) -> tuple[str, str]:
        return self.template_for(kind)(recipient, params, app_base_url)

    def template_for(self, kind: NotificationKind) -> NotificationTemplate:
        try:
            return self._templates[kind]
        except KeyError:
            raise MissingNotificationTemplateError(kind) from None
