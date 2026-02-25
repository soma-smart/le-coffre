import logging
from typing import Optional

from vault_management_context.application.commands import CreateVaultCommand
from vault_management_context.domain.entities import Vault
from vault_management_context.domain.value_objects import VaultConfiguration
from vault_management_context.domain.services import (
    VaultCreationService,
)
from vault_management_context.application.gateways import (
    VaultRepository,
    ShamirGateway,
    EncryptionGateway,
    VaultSessionGateway,
    VaultEventRepository,
)
from vault_management_context.application.services import KeySessionManager
from vault_management_context.application.responses.vault_setup_response import (
    VaultSetupResponse,
)
from vault_management_context.domain.events import VaultCreatedEvent
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase

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
    ) -> None:
        self.vault_repo = vault_repo
        self.shamir_gateway = shamir_gateway
        self.encryption_gateway = encryption_gateway
        self.vault_session_gateway = vault_session_gateway
        self._event_publisher = event_publisher
        self._vault_event_repository = vault_event_repository

    def execute(self, command: CreateVaultCommand) -> VaultSetupResponse:
        existing_vault: Optional[Vault] = self.vault_repo.get()
        configuration = VaultConfiguration.create(command.nb_shares, command.threshold)

        VaultCreationService.ensure_creation_allowed(existing_vault)

        shamir_result = self.shamir_gateway.create_shares(configuration)

        encrypted_key = self.encryption_gateway.generate_vault_key(
            shamir_result.master_key
        )

        vault = VaultCreationService.create_vault_entity(
            configuration, encrypted_key, str(command.setup_id)
        )

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
            event_data={"setup_id": str(command.setup_id), "nb_shares": command.nb_shares, "threshold": command.threshold},
        )

        return VaultSetupResponse(
            setup_id=str(command.setup_id), shares=shamir_result.shares
        )
