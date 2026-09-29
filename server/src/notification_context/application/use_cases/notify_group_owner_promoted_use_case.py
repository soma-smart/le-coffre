import logging

from notification_context.application.commands import NotifyGroupOwnerPromotedCommand
from notification_context.application.gateways import GroupOwnershipGateway
from shared_kernel.application.gateways import EmailGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


class NotifyGroupOwnerPromotedUseCase(TracedUseCase):
    def __init__(self, group_ownership_gateway: GroupOwnershipGateway, email_gateway: EmailGateway, app_base_url: str):
        self._group_ownership_gateway = group_ownership_gateway
        self._email_gateway = email_gateway
        self._app_base_url = app_base_url

    def execute(self, command: NotifyGroupOwnerPromotedCommand) -> None:
        try:
            details = self._group_ownership_gateway.get_owner_promotion_details(command.user_id, command.group_id)
        except Exception:  # noqa: BLE001 - reactive/courtesy send: an unexpected lookup failure must never surface as an error on the already-successful promotion request
            logger.error(
                "Failed to look up owner-promotion details for user=%s group=%s",
                command.user_id,
                command.group_id,
                exc_info=True,
            )
            return

        if details is None:
            logger.warning(
                "No owner-promotion details found for user=%s group=%s; skipping notification email",
                command.user_id,
                command.group_id,
            )
            return

        subject = f'You\'re now an owner of "{details.group_name}"'
        body = (
            f"Hello {details.display_name},\n\n"
            f'You\'ve been made an owner of the group "{details.group_name}".\n\n'
            f"{self._app_base_url}/groups"
        )

        try:
            self._email_gateway.send(to=details.email, subject=subject, body=body)
        except EmailDeliveryError:
            logger.error(
                "Failed to send owner-promotion email to %s for group %s",
                details.email,
                details.group_name,
                exc_info=True,
            )
