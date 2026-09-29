from identity_access_management_context.domain.events import ExtensionPairedEvent
from notification_context.application.commands import NotifyExtensionPairedCommand
from notification_context.application.use_cases import NotifyExtensionPairedUseCase


class ExtensionPairedEventSubscriber:
    """Primary adapter subscribing to ExtensionPairedEvent to trigger the owner's email."""

    def __init__(self, notify_use_case: NotifyExtensionPairedUseCase):
        self._notify_use_case = notify_use_case

    def handle(self, event: ExtensionPairedEvent) -> None:
        self._notify_use_case.execute(
            NotifyExtensionPairedCommand(
                user_id=event.user_id,
                device_name=event.device_name,
                created_from_ip=event.created_from_ip,
                paired_at=event.occurred_on,
            )
        )
