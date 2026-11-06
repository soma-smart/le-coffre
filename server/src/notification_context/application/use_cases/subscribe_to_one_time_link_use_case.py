from notification_context.application.commands import SubscribeToOneTimeLinkCommand
from notification_context.application.gateways import OneTimeLinkGateway, OneTimeLinkSubscriptionRepository
from notification_context.domain.entities import OneTimeLinkSubscription
from notification_context.domain.exceptions import OneTimeLinkNoLongerActiveError, OneTimeLinkNotFoundError
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class SubscribeToOneTimeLinkUseCase(TracedUseCase):
    """Lets the creator of a one-time link choose to be emailed when it is opened,
    and / or when it expires without having been opened.

    Only the creator can follow a link, and only while it can still be read.
    Choosing neither option removes the subscription.
    """

    def __init__(
        self,
        repository: OneTimeLinkSubscriptionRepository,
        one_time_link_gateway: OneTimeLinkGateway,
        time_gateway: TimeGateway,
    ):
        self._repository = repository
        self._one_time_link_gateway = one_time_link_gateway
        self._time_gateway = time_gateway

    def execute(self, command: SubscribeToOneTimeLinkCommand) -> OneTimeLinkSubscription:
        link = self._one_time_link_gateway.get_link(command.link_id)
        if link is None or link.created_by_user_id != command.user_id:
            raise OneTimeLinkNotFoundError()
        if not link.is_active(self._time_gateway.get_current_time()):
            raise OneTimeLinkNoLongerActiveError()

        subscription = OneTimeLinkSubscription(
            link_id=link.link_id,
            user_id=command.user_id,
            expires_at=link.expires_at,
            notify_on_read=command.notify_on_read,
            notify_on_expiry=command.notify_on_expiry,
        )
        if subscription.is_empty():
            self._repository.remove(link.link_id)
        else:
            self._repository.save(subscription)
        return subscription
