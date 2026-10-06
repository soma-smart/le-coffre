import logging

from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
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
from vault_management_context.application.services import KeySessionManager
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

    def execute(self, command: CreateVaultCommand) -> VaultSetupResponse:
        existing_vault: Vault | None = self.vault_repo.get()
        configuration = VaultConfiguration.create(command.nb_shares, command.threshold)

        VaultCreationService.ensure_creation_allowed(existing_vault)

        shamir_result = self.shamir_gateway.create_shares(configuration)

        encrypted_key = self.encryption_gateway.generate_vault_key(shamir_result.master_key)

        vault = VaultCreationService.create_vault_entity(configuration, encrypted_key, str(command.setup_id))

        # Always store the session key when creating vault
        # Clear any existing session key first (for re-setup scenario)
        if not self.vault_session_gateway.is_vault_locked():
            self.vault_session_gateway.clear_decrypted_key()

        KeySessionManager.decrypt_and_store_key(
            self.encryption_gateway,
            self.vault_session_gateway,
            vault.encrypted_key,
            shamir_result.master_key,
        )

        self.vault_repo.save(vault)

        issued_links = self._issue_share_links(shamir_result.shares, str(command.setup_id))

        logger.info("Vault created (nb_shares=%d, threshold=%d)", command.nb_shares, command.threshold)
        event = VaultCreatedEvent(
            setup_id=str(command.setup_id),
            nb_shares=command.nb_shares,
            threshold=command.threshold,
        )
        self._event_publisher.publish(event)
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

        return VaultSetupResponse(setup_id=str(command.setup_id), share_links=issued_links)

    def _issue_share_links(self, shares: list[Share], setup_id: str) -> list[IssuedShareLink]:
        """Seal every share behind its own single-use link.

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
                sealed_share=self._share_sealing_gateway.seal(share, token),
                now=now,
            )
            links.append(link)
            issued.append(IssuedShareLink(share_index=share_index, token=token.value, expires_at=link.expires_at))

        self._share_link_repository.replace_all(links)
        return issued
