from identity_access_management_context.domain.events import OwnerAddedToGroupEvent
from notification_context.application.commands import NotifyGroupOwnerPromotedCommand
from notification_context.application.use_cases import NotifyGroupOwnerPromotedUseCase


class GroupOwnerPromotedEventSubscriber:
    """Primary adapter subscribing to OwnerAddedToGroupEvent to trigger the owner-promotion email."""

    def __init__(self, notify_use_case: NotifyGroupOwnerPromotedUseCase):
        self._notify_use_case = notify_use_case

    def handle(self, event: OwnerAddedToGroupEvent) -> None:
        command = NotifyGroupOwnerPromotedCommand(
            group_id=event.group_id,
            user_id=event.user_id,
            added_by_user_id=event.added_by_user_id,
        )
        self._notify_use_case.execute(command)
