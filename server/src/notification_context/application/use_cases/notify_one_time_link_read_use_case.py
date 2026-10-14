import logging

from notification_context.application.commands import NotifyOneTimeLinkReadCommand
from notification_context.application.gateways import OneTimeLinkSubscriptionRepository, RecipientGateway
from notification_context.domain.emails import one_time_link_opened_email
from shared_kernel.application.gateways import EmailGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import EmailDeliveryError

logger = logging.getLogger(__name__)


class NotifyOneTimeLinkReadUseCase(TracedUseCase):
    """Tells the creator of a one-time link that it was just opened, if they asked to be.

    The subscription is removed whether or not the creator asked for this email: a
    link that was read will not expire unused, so the expiry sweep must not see it.
    Only the caller that removes it sends anything, see
    OneTimeLinkSubscriptionRepository.remove().

    Courtesy send: the secret was already released, so an unknown recipient or a
    failing relay is logged and never raised.
    """

    def __init__(
        self,
        repository: OneTimeLinkSubscriptionRepository,
        recipient_gateway: RecipientGateway,
        email_gateway: EmailGateway,
        app_base_url: str,
    ):
        self._repository = repository
        self._recipient_gateway = recipient_gateway
        self._email_gateway = email_gateway
        self._app_base_url = app_base_url

    def execute(self, command: NotifyOneTimeLinkReadCommand) -> None:
        subscription = self._repository.get(command.link_id)
        if subscription is None or not self._repository.remove(command.link_id):
            return
        if not subscription.notify_on_read:
            return

        recipients = self._recipient_gateway.get_recipients([subscription.user_id])
        if not recipients:
            logger.warning("Not sending the one-time link opened email: user %s not found", subscription.user_id)
            return

        email = one_time_link_opened_email(recipients[0], command.password_name, command.read_at, self._app_base_url)
        try:
            self._email_gateway.send(email.to, email.subject, email.body)
        except EmailDeliveryError as error:
            logger.error("Failed to send the one-time link opened email to user %s: %s", subscription.user_id, error)
