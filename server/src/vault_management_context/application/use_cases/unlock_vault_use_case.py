import logging

from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase
from vault_management_context.application.commands import UnlockVaultCommand
from vault_management_context.application.gateways import (
    EncryptionGateway,
    ShamirGateway,
    ShareRepository,
    VaultEventRepository,
    VaultRepository,
    VaultSessionGateway,
)
from vault_management_context.application.services import KeySessionManager
from vault_management_context.domain.entities import Share
from vault_management_context.domain.events import VaultUnlockedEvent
from vault_management_context.domain.exceptions import (
    ShareReconstructionError,
    VaultNotSetupException,
    VaultUnlockedError,
)

logger = logging.getLogger(__name__)


class UnlockVaultUseCase(TracedUseCase):
    def __init__(
        self,
        vault_repository: VaultRepository,
        shamir_gateway: ShamirGateway,
        encryption_gateway: EncryptionGateway,
        vault_session_gateway: VaultSessionGateway,
        share_repository: ShareRepository,
        event_publisher: DomainEventPublisher,
        vault_event_repository: VaultEventRepository,
    ):
        self._vault_repository = vault_repository
        self._shamir_gateway = shamir_gateway
        self._encryption_gateway = encryption_gateway
        self._vault_session_gateway = vault_session_gateway
        self._share_repository = share_repository
        self._event_publisher = event_publisher
        self._vault_event_repository = vault_event_repository

    def execute(self, command: UnlockVaultCommand) -> None:
        vault = self._vault_repository.get()
        if vault is None:
            raise VaultNotSetupException()

        # Only the shares of this unlock session take part in the reconstruction:
        # a bad share submitted to another session cannot spoil this one.
        existing_shares = self._share_repository.get_all(command.session_id)
        # Domain invariant: a share must not count twice toward the threshold.
        # Dedupe the submission against the already-pending pool (and against
        # itself) here, in the application layer, so the store stays a dumb sink.
        new_shares = self._deduplicate(command.shares, existing_shares)
        # A legitimate session never holds more distinct shares than the vault has:
        # anything beyond is dropped, bounding what a flood can pile into a session.
        new_shares = new_shares[: max(vault.nb_shares - len(existing_shares), 0)]
        all_shares = existing_shares + new_shares

        try:
            master_secret = self._shamir_gateway.reconstruct_secret(all_shares)

            KeySessionManager.decrypt_and_store_key(
                self._encryption_gateway,
                self._vault_session_gateway,
                vault.encrypted_key,
                master_secret,
            )

            # Once unlocked, every pending session is obsolete, not only this one.
            self._share_repository.clear()
            logger.info("Vault unlocked", extra={"share_count": len(all_shares)})
            event = VaultUnlockedEvent()
            self._event_publisher.publish(event)
            self._vault_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=None,
                event_data={},
            )
        except VaultUnlockedError as e:
            raise e
        except Exception as e:
            self._share_repository.add(command.session_id, new_shares)
            raise ShareReconstructionError() from e

    @staticmethod
    def _deduplicate(new_shares: list[Share], existing_shares: list[Share]) -> list[Share]:
        seen = {share.secret for share in existing_shares}
        deduped: list[Share] = []
        for share in new_shares:
            if share.secret not in seen:
                deduped.append(share)
                seen.add(share.secret)
        return deduped
