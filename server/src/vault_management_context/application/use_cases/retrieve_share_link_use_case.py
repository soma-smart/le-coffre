import logging

from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway, TransactionGateway
from shared_kernel.application.tracing import TracedUseCase
from vault_management_context.application.commands import RetrieveShareLinkCommand
from vault_management_context.application.gateways import ShareLinkRepository, VaultEventRepository
from vault_management_context.application.responses import RetrievedShareLink
from vault_management_context.domain.events import VaultShareLinkRetrievedEvent
from vault_management_context.domain.exceptions import ShareLinkUnusableError
from vault_management_context.domain.value_objects import ShareLinkLookupHash

logger = logging.getLogger(__name__)


class RetrieveShareLinkUseCase(TracedUseCase):
    """Hand a custodian the sealed share behind their link. No authentication.

    The link is not deleted here: the share is only safe once the custodian's
    browser has opened it and they have saved it somewhere, which the server
    cannot see. The first opening starts a short reopen window instead, and the
    link goes when the custodian acknowledges it (AcknowledgeShareLinkUseCase)
    or when the window runs out. Every opening after the first is flagged, so a
    custodian who did not open it before learns someone else did.

    Works whatever the vault state: nothing here needs the vault key, which is
    what keeps the links usable after a restart, i.e. exactly when the shares
    are needed to unlock.
    """

    def __init__(
        self,
        share_link_repository: ShareLinkRepository,
        event_publisher: DomainEventPublisher,
        vault_event_repository: VaultEventRepository,
        time_gateway: TimeGateway,
        transaction_gateway: TransactionGateway,
    ) -> None:
        self._share_link_repository = share_link_repository
        self._event_publisher = event_publisher
        self._vault_event_repository = vault_event_repository
        self._time_gateway = time_gateway
        self._transaction_gateway = transaction_gateway

    def execute(self, command: RetrieveShareLinkCommand) -> RetrievedShareLink:
        lookup_hash = ShareLinkLookupHash(command.lookup_hash)
        now = self._time_gateway.get_current_time()

        # Expired links are purged on a timer, not here: this endpoint is
        # anonymous, and a lookup must not cost a write.
        link = self._share_link_repository.get_by_lookup_hash(lookup_hash.value)
        if link is None or not link.can_be_delivered(now):
            raise ShareLinkUnusableError()

        # Each delivery goes only together with its audit record: that record
        # is how a share retrieved by someone else gets noticed.
        with self._transaction_gateway.atomic():
            delivery = self._share_link_repository.deliver(link.id, now, link.reopen_deadline(now))
            if delivery is None:
                raise ShareLinkUnusableError()
            event = VaultShareLinkRetrievedEvent(
                setup_id=link.setup_id, share_index=link.share_index, reopened=delivery.reopened
            )
            self._vault_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=None,
                event_data={
                    "setup_id": link.setup_id,
                    "share_index": link.share_index,
                    "reopened": delivery.reopened,
                },
            )

        logger.info(
            "Vault share link retrieved",
            extra={"share_index": link.share_index, "reopened": delivery.reopened},
        )
        self._event_publisher.publish(event)

        return RetrievedShareLink(
            setup_id=link.setup_id,
            share_index=link.share_index,
            sealed_share=link.sealed_share,
            first_retrieved_at=delivery.first_delivered_at,
            reopenable_until=delivery.reopenable_until,
            reopened=delivery.reopened,
        )
