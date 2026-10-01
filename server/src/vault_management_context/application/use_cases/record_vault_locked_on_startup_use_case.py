import logging

from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase
from vault_management_context.application.gateways import (
    VaultEventRepository,
    VaultRepository,
)
from vault_management_context.domain.events import (
    VaultCreatedEvent,
    VaultLockedEvent,
    VaultUnlockedEvent,
)

logger = logging.getLogger(__name__)

# Events that leave the vault unlocked (setup unlocks it right away) or locked.
_LOCK_STATE_EVENT_TYPES = [
    VaultCreatedEvent.__name__,
    VaultUnlockedEvent.__name__,
    VaultLockedEvent.__name__,
]


class RecordVaultLockedOnStartupUseCase(TracedUseCase):
    """Records that a server start locked the vault, once per lock.

    The decrypted key only lives in memory, so every start leaves the vault locked,
    whatever it was before. That is a real lock (share holders must unlock it
    again), so it is recorded and published like one — but only when the vault was
    last known unlocked: a server restarting in a loop while the vault stays locked
    must not report the same lock again at every start.
    """

    def __init__(
        self,
        vault_repository: VaultRepository,
        event_publisher: DomainEventPublisher,
        vault_event_repository: VaultEventRepository,
    ):
        self._vault_repository = vault_repository
        self._event_publisher = event_publisher
        self._vault_event_repository = vault_event_repository

    def execute(self) -> None:
        if self._vault_repository.get() is None:
            return

        last_event_type = self._vault_event_repository.get_last_event_type(_LOCK_STATE_EVENT_TYPES)
        if last_event_type == VaultLockedEvent.__name__:
            return

        logger.info("Vault locked by server start")
        event = VaultLockedEvent(locked_by_user_id=None)
        # append_event() before publish(): the DB is least stable right here, just
        # after migrations. If it fails, execute() raises before any notification
        # email is sent (the caller logs and moves on; the next start retries from
        # scratch) instead of an email going out for a lock that was never durably
        # recorded, which the next start would then report — and email — again.
        self._vault_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=None,
            event_data={"reason": "server_start"},
        )
        self._event_publisher.publish(event)
