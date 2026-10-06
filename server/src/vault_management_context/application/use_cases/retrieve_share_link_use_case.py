import logging

from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from vault_management_context.application.commands import RetrieveShareLinkCommand
from vault_management_context.application.gateways import ShareLinkRepository, VaultEventRepository
from vault_management_context.application.responses import RetrievedShareLink
from vault_management_context.domain.events import VaultShareLinkRetrievedEvent
from vault_management_context.domain.exceptions import ShareLinkUnusableError
from vault_management_context.domain.value_objects import ShareLinkLookupHash

logger = logging.getLogger(__name__)


class RetrieveShareLinkUseCase(TracedUseCase):
    """Hand a custodian the sealed share behind their link, once. No authentication.

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
    ) -> None:
        self._share_link_repository = share_link_repository
        self._event_publisher = event_publisher
        self._vault_event_repository = vault_event_repository
        self._time_gateway = time_gateway

    def execute(self, command: RetrieveShareLinkCommand) -> RetrievedShareLink:
        lookup_hash = ShareLinkLookupHash(command.lookup_hash)
        now = self._time_gateway.get_current_time()

        # Housekeeping on the way: an expired link can never be used, so its
        # ciphertext has no reason to stay in the database.
        self._share_link_repository.purge_expired(now)

        link = self._share_link_repository.get_by_lookup_hash(lookup_hash.value)
        if link is None:
            raise ShareLinkUnusableError()
        link.ensure_not_expired(now)

        # Single conditional delete. Two concurrent retrievals both reach here,
        # only one gets True.
        if not self._share_link_repository.consume(link.id, now):
            raise ShareLinkUnusableError()

        logger.info("Vault share link retrieved", extra={"share_index": link.share_index})
        event = VaultShareLinkRetrievedEvent(setup_id=link.setup_id, share_index=link.share_index)
        self._event_publisher.publish(event)
        self._vault_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=None,
            event_data={"setup_id": link.setup_id, "share_index": link.share_index},
        )

        return RetrievedShareLink(share_index=link.share_index, sealed_share=link.sealed_share)
