import logging

from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway, TransactionGateway
from shared_kernel.application.tracing import TracedUseCase
from vault_management_context.application.commands import AcknowledgeShareLinkCommand
from vault_management_context.application.gateways import ShareLinkRepository, VaultEventRepository
from vault_management_context.domain.events import VaultShareLinkAcknowledgedEvent
from vault_management_context.domain.exceptions import ShareLinkAckRejectedError, ShareLinkUnusableError
from vault_management_context.domain.value_objects import ShareLinkAckKey, ShareLinkLookupHash

logger = logging.getLogger(__name__)


class AcknowledgeShareLinkUseCase(TracedUseCase):
    """Close a share link once its custodian has saved the share. No authentication.

    Takes a key derived from the token, not just the lookup hash: whoever can
    read the database knows every lookup hash, and must not be able to close a
    link in its custodian's place. A link can only be acknowledged after being
    delivered, since until then there is nothing for the custodian to have
    saved, and before its reopen window ends: past it, the link closed on its
    own, and the audit trail must say so rather than show a confirmation.
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

    def execute(self, command: AcknowledgeShareLinkCommand) -> None:
        lookup_hash = ShareLinkLookupHash(command.lookup_hash)
        ack_key = ShareLinkAckKey(command.ack_key)
        now = self._time_gateway.get_current_time()

        link = self._share_link_repository.get_by_lookup_hash(lookup_hash.value)
        if link is None or not link.can_be_acknowledged(now):
            raise ShareLinkUnusableError()
        if not link.accepts_ack(ack_key.as_bytes()):
            raise ShareLinkAckRejectedError()

        event = VaultShareLinkAcknowledgedEvent(setup_id=link.setup_id, share_index=link.share_index)
        with self._transaction_gateway.atomic():
            if not self._share_link_repository.remove_delivered(link.id, now):
                raise ShareLinkUnusableError()
            self._vault_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=None,
                event_data={"setup_id": link.setup_id, "share_index": link.share_index},
            )

        logger.info("Vault share link acknowledged", extra={"share_index": link.share_index})
        self._event_publisher.publish(event)
