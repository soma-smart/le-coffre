import logging

from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway, TransactionGateway
from shared_kernel.application.tracing import TracedUseCase
from vault_management_context.application.commands import CreateVaultCommand
from vault_management_context.application.gateways import (
    EncryptionGateway,
    ShamirGateway,
    ShareLinkRepository,
    ShareSealingGateway,
    VaultEventRepository,
    VaultRepository,
    VaultSessionGateway,
)
from vault_management_context.application.responses import IssuedShareLink, VaultSetupResponse
from vault_management_context.domain.entities import Share, ShareLink, Vault
from vault_management_context.domain.events import VaultCreatedEvent
from vault_management_context.domain.services import (
    VaultCreationService,
)
from vault_management_context.domain.value_objects import ShareLinkToken, VaultConfiguration

logger = logging.getLogger(__name__)


class CreateVaultUseCase(TracedUseCase):
    def __init__(
        self,
        vault_repo: VaultRepository,
        shamir_gateway: ShamirGateway,
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
        event_publisher: DomainEventPublisher,
        vault_event_repository: VaultEventRepository,
        share_link_repository: ShareLinkRepository,
        share_sealing_gateway: ShareSealingGateway,
        time_gateway: TimeGateway,
        transaction_gateway: TransactionGateway,
    ) -> None:
        self.vault_repo = vault_repo
        self.shamir_gateway = shamir_gateway
        self.encryption_gateway = encryption_gateway
        self.vault_session_gateway = vault_session_gateway
        self._event_publisher = event_publisher
        self._vault_event_repository = vault_event_repository
        self._share_link_repository = share_link_repository
        self._share_sealing_gateway = share_sealing_gateway
        self._time_gateway = time_gateway
        self._transaction_gateway = transaction_gateway

    def execute(self, command: CreateVaultCommand) -> VaultSetupResponse:
        existing_vault: Vault | None = self.vault_repo.get()
        configuration = VaultConfiguration.create(command.nb_shares, command.threshold)

        VaultCreationService.ensure_creation_allowed(existing_vault)

        shamir_result = self.shamir_gateway.create_shares(configuration)

        encrypted_key = self.encryption_gateway.generate_vault_key(shamir_result.master_key)

        vault = VaultCreationService.create_vault_entity(configuration, encrypted_key, str(command.setup_id))

        # Decrypted now, kept in memory only once the setup is committed: a
        # failed setup must leave neither a half-written vault nor a key that
        # matches nothing in the database.
        decrypted_key = self.encryption_gateway.decrypt(vault.encrypted_key, shamir_result.master_key)
        event = VaultCreatedEvent(
            setup_id=str(command.setup_id),
            nb_shares=command.nb_shares,
            threshold=command.threshold,
        )

        # One transaction: a PENDING vault without its links would hold shares
        # nobody can ever retrieve.
        with self._transaction_gateway.atomic():
            self.vault_repo.save(vault)
            issued_links = self._issue_share_links(shamir_result.shares, str(command.setup_id))
            self._vault_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=None,
                event_data={
                    "setup_id": str(command.setup_id),
                    "nb_shares": command.nb_shares,
                    "threshold": command.threshold,
                },
            )

        # Clear the key of an earlier, abandoned setup before storing this one
        if not self.vault_session_gateway.is_vault_locked():
            self.vault_session_gateway.clear_decrypted_key()
        self.vault_session_gateway.store_decrypted_key(decrypted_key)

        logger.info("Vault created (nb_shares=%d, threshold=%d)", command.nb_shares, command.threshold)
        self._event_publisher.publish(event)

        return VaultSetupResponse(setup_id=str(command.setup_id), share_links=issued_links)

    def _issue_share_links(self, shares: list[Share], setup_id: str) -> list[IssuedShareLink]:
        """Seal every share behind its own link, closed by its custodian once saved.

        The shares never leave this method in clear: what is stored is sealed
        under a key derived from a token the server forgets as soon as the
        response is sent, and what is returned is only those tokens. Replacing
        rather than adding drops the links of an earlier, abandoned setup, whose
        shares belong to a master key that no longer exists.
        """
        now = self._time_gateway.get_current_time()
        links: list[ShareLink] = []
        issued: list[IssuedShareLink] = []
        for share_index, share in enumerate(shares, start=1):
            token = ShareLinkToken.generate()
            link = ShareLink.create(
                setup_id=setup_id,
                share_index=share_index,
                lookup_hash=token.lookup_hash(),
                ack_hash=self._share_sealing_gateway.ack_hash(token),
                sealed_share=self._share_sealing_gateway.seal(share, token, setup_id, share_index),
                now=now,
            )
            links.append(link)
            issued.append(IssuedShareLink(share_index=share_index, token=token.value, expires_at=link.expires_at))

        self._share_link_repository.replace_all(links)
        return issued
