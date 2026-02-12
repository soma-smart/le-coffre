from vault_management_context.application.commands import LockVaultCommand
from vault_management_context.application.gateways import (
    VaultRepository,
    VaultSessionGateway,
    VaultEventRepository,
)
from vault_management_context.domain.exceptions import (
    VaultNotSetupException,
    VaultLockedException,
)
from shared_kernel.domain.services import AdminPermissionChecker
from vault_management_context.domain.events import VaultLockedEvent
from shared_kernel.application.gateways import DomainEventPublisher


class LockVaultUseCase:
    def __init__(
        self,
        vault_repository: VaultRepository,
        vault_session_gateway: VaultSessionGateway,
        event_publisher: DomainEventPublisher,
        vault_event_repository: VaultEventRepository,
    ):
        self._vault_repository = vault_repository
        self._vault_session_gateway = vault_session_gateway
        self._event_publisher = event_publisher
        self._vault_event_repository = vault_event_repository

    def execute(self, command: LockVaultCommand) -> None:
        """Lock the vault by clearing the decrypted key from memory"""
        AdminPermissionChecker().ensure_admin(command.requesting_user, "lock the vault")

        vault = self._vault_repository.get()
        if vault is None:
            raise VaultNotSetupException()

        try:
            self._vault_session_gateway.get_decrypted_key()
        except ValueError:
            raise VaultLockedException()

        self._vault_session_gateway.clear_decrypted_key()

        event = VaultLockedEvent(locked_by_user_id=command.requesting_user.user_id)
        self._event_publisher.publish(event)
        self._vault_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.requesting_user.user_id,
            event_data={},
        )
