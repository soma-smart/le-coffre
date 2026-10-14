import logging

from notification_context.application.gateways import (
    OneTimeLinkGateway,
    OneTimeLinkSubscriptionRepository,
    RecipientGateway,
)
from notification_context.domain.emails import one_time_link_expired_unused_email, one_time_link_opened_email
from notification_context.domain.entities import OneTimeLinkSubscription
from notification_context.domain.value_objects import OneTimeLinkDetails
from shared_kernel.application.gateways import EmailGateway, TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import EmailDeliveryError
from shared_kernel.domain.value_objects import OutgoingEmail

logger = logging.getLogger(__name__)

# Upper bound on the subscriptions handled per pass, so one pass never loads an
# unbounded table. A larger backlog is simply worked through over the next passes.
EXPIRY_SWEEP_BATCH_SIZE = 100


class NotifyExpiredOneTimeLinksUseCase(TracedUseCase):
    """System use case: tells the creators whose one-time link expired unused.

    Expiry is passive (a clock comparison), so nothing happens when a link runs out:
    this runs periodically over the subscriptions whose link has expired, and
    settles each of them by removing it.

    The link's state is read from the password context *before* the subscription is
    removed, and the email sent is the one that matches that state. A link read just
    before it expired, whose read notification has not been handled yet, therefore
    gets its "opened" email from here, and the read notification then finds nothing
    to remove. Either way, a link produces at most one email.

    Delivery is at most once: a subscription is removed before its email is sent.
    """

    def __init__(
        self,
        repository: OneTimeLinkSubscriptionRepository,
        one_time_link_gateway: OneTimeLinkGateway,
        recipient_gateway: RecipientGateway,
        email_gateway: EmailGateway,
        time_gateway: TimeGateway,
        app_base_url: str,
        batch_size: int = EXPIRY_SWEEP_BATCH_SIZE,
    ):
        self._repository = repository
        self._one_time_link_gateway = one_time_link_gateway
        self._recipient_gateway = recipient_gateway
        self._email_gateway = email_gateway
        self._time_gateway = time_gateway
        self._app_base_url = app_base_url
        self._batch_size = batch_size

    def execute(self) -> int:
        """Settle one batch of expired subscriptions; returns how many emails were sent."""
        now = self._time_gateway.get_current_time()
        to_notify: list[tuple[OneTimeLinkSubscription, OneTimeLinkDetails]] = []

        for subscription in self._repository.list_expired(now, self._batch_size):
            try:
                link = self._one_time_link_gateway.get_link(subscription.link_id)
            except Exception:  # noqa: BLE001 - left in place, the next pass tries again
                logger.error("Failed to look up one-time link %s", subscription.link_id, exc_info=True)
                continue
            if not self._repository.remove(subscription.link_id):
                continue  # settled meanwhile, by a read or by another replica
            # Gone with its password, or revoked: there is nothing to tell.
            if link is not None and self._wants_email_for(subscription, link):
                to_notify.append((subscription, link))

        return self._send(to_notify)

    @staticmethod
    def _wants_email_for(subscription: OneTimeLinkSubscription, link: OneTimeLinkDetails) -> bool:
        if link.read_at is not None:
            return subscription.notify_on_read
        return link.revoked_at is None and subscription.notify_on_expiry

    def _send(self, to_notify: list[tuple[OneTimeLinkSubscription, OneTimeLinkDetails]]) -> int:
        if not to_notify:
            return 0
        recipients = {
            recipient.user_id: recipient
            for recipient in self._recipient_gateway.get_recipients(list({s.user_id for s, _ in to_notify}))
        }
        emails: list[OutgoingEmail] = []
        for subscription, link in to_notify:
            recipient = recipients.get(subscription.user_id)
            if recipient is None:
                logger.warning("Not sending a one-time link email: user %s not found", subscription.user_id)
                continue
            if link.read_at is not None:
                emails.append(
                    one_time_link_opened_email(recipient, link.password_name, link.read_at, self._app_base_url)
                )
            else:
                emails.append(
                    one_time_link_expired_unused_email(
                        recipient, link.password_name, link.expires_at, self._app_base_url
                    )
                )
        if not emails:
            return 0

        try:
            # One connection to the relay for the whole batch.
            failures = self._email_gateway.send_bulk(emails)
        except EmailDeliveryError as error:
            logger.error("Failed to send any of %d one-time link email(s): %s", len(emails), error)
            return 0
        for to, error in failures:
            logger.error("Failed to send a one-time link email to %s: %s", to, error)

        sent = len(emails) - len(failures)
        logger.info("Sent %d one-time link expiry email(s)", sent)
        return sent
