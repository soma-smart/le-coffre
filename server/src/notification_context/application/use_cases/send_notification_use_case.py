import logging

from notification_context.application.commands import SendNotificationCommand
from notification_context.application.gateways import RecipientGateway
from notification_context.application.templates import NotificationCatalog
from shared_kernel.application.gateways import EmailGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


class SendNotificationUseCase(TracedUseCase):
    """Sends one notification email to one user, whatever the kind of notification.

    Knows nothing about any particular kind: who the recipient is comes from the
    RecipientGateway, how the email reads comes from the catalog. A new kind of
    notification therefore never touches this class.

    Notifications are courtesy emails: an unknown recipient or a failing relay is
    logged and swallowed, never raised at whoever triggered the notification. A kind
    with no template is different: that is a programming error and it does raise.
    """

    def __init__(
        self,
        recipient_gateway: RecipientGateway,
        email_gateway: EmailGateway,
        catalog: NotificationCatalog,
        app_base_url: str,
    ):
        self._recipient_gateway = recipient_gateway
        self._email_gateway = email_gateway
        self._catalog = catalog
        self._app_base_url = app_base_url

    def execute(self, command: SendNotificationCommand) -> None:
        notification = command.notification

        # Resolved first so that a missing template is reported even when the
        # recipient happens to be gone, instead of hiding behind that early return.
        self._catalog.template_for(notification.kind)

        recipients = self._recipient_gateway.get_recipients([notification.recipient_user_id])
        if not recipients:
            logger.warning(
                "Not sending %s notification: recipient %s not found",
                notification.kind.value,
                notification.recipient_user_id,
            )
            return
        recipient = recipients[0]

        subject, body = self._catalog.render(notification.kind, recipient, notification.params, self._app_base_url)

        try:
            self._email_gateway.send(recipient.email, subject, body)
        except EmailDeliveryError as error:
            logger.error(
                "Failed to send %s notification to user %s: %s",
                notification.kind.value,
                notification.recipient_user_id,
                error,
            )
