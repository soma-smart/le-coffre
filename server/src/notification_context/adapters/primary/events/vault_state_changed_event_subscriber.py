import logging
from concurrent.futures import Executor
from typing import Callable

from sqlmodel import Session

from notification_context.adapters.secondary.sql import SqlNotificationPreferencesRepository
from notification_context.application.commands import NotifyVaultStateChangedCommand
from notification_context.application.gateways import RecipientGateway
from notification_context.application.use_cases import NotifyVaultStateChangedUseCase
from notification_context.domain.value_objects import VaultStateChange
from shared_kernel.application.gateways import EmailGateway
from vault_management_context.domain.events import VaultLockedEvent, VaultUnlockedEvent

logger = logging.getLogger(__name__)


class VaultStateChangedEventSubscriber:
    """Primary adapter subscribing to VaultLockedEvent / VaultUnlockedEvent to email opted-in users.

    Events are published from inside the lock / unlock request (and at server start).
    Sending one email per subscriber must not hold that request, so the work is handed
    to an executor. A single-worker executor also keeps the emails of a lock and of the
    following unlock in order.
    """

    def __init__(
        self,
        session_maker: Callable[[], Session],
        recipient_gateway: RecipientGateway,
        email_gateway: EmailGateway,
        app_base_url: str,
        executor: Executor,
    ):
        self._session_maker = session_maker
        self._recipient_gateway = recipient_gateway
        self._email_gateway = email_gateway
        self._app_base_url = app_base_url
        self._executor = executor

    def handle_locked(self, event: VaultLockedEvent) -> None:
        self._submit(
            NotifyVaultStateChangedCommand(change=VaultStateChange.LOCKED, locked_by_user_id=event.locked_by_user_id)
        )

    def handle_unlocked(self, event: VaultUnlockedEvent) -> None:
        self._submit(NotifyVaultStateChangedCommand(change=VaultStateChange.UNLOCKED))

    def _submit(self, command: NotifyVaultStateChangedCommand) -> None:
        # publish() calls subscribers synchronously with no safety net, from inside
        # LockVaultUseCase/UnlockVaultUseCase, before the vault event is persisted:
        # submit() raising (e.g. the executor was already shut down) must not escape
        # as a 500 on an otherwise-successful lock/unlock, nor skip the audit event.
        try:
            self._executor.submit(self._notify, command)
        except Exception:  # noqa: BLE001 - courtesy emails: a failure is logged, never raised into the caller
            logger.error("Failed to submit vault %s notifications", command.change.value, exc_info=True)

    def _notify(self, command: NotifyVaultStateChangedCommand) -> None:
        try:
            with self._session_maker() as session:
                NotifyVaultStateChangedUseCase(
                    SqlNotificationPreferencesRepository(session),
                    self._recipient_gateway,
                    self._email_gateway,
                    self._app_base_url,
                ).execute(command)
        except Exception:  # noqa: BLE001 - courtesy emails: a failure is logged, never raised into the executor
            logger.error("Failed to send vault %s notifications", command.change.value, exc_info=True)
