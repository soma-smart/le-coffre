import logging
from concurrent.futures import Executor
from typing import Callable

from sqlmodel import Session

from notification_context.adapters.secondary.sql import SqlOneTimeLinkSubscriptionRepository
from notification_context.application.commands import NotifyOneTimeLinkReadCommand
from notification_context.application.gateways import RecipientGateway
from notification_context.application.use_cases import NotifyOneTimeLinkReadUseCase
from password_management_context.domain.events import OneTimeLinkReadEvent
from shared_kernel.application.gateways import EmailGateway

logger = logging.getLogger(__name__)


class OneTimeLinkReadEventSubscriber:
    """Primary adapter subscribing to OneTimeLinkReadEvent to email the link's creator.

    The event is published inside the anonymous consumption request, and sending an
    email can take as long as the relay's connection timeout. The work is therefore
    handed to an executor, so the recipient of the link never waits on it.
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

    def handle(self, event: OneTimeLinkReadEvent) -> None:
        self._executor.submit(
            self._notify,
            NotifyOneTimeLinkReadCommand(
                link_id=event.link_id, password_name=event.password_name, read_at=event.read_at
            ),
        )

    def _notify(self, command: NotifyOneTimeLinkReadCommand) -> None:
        # Runs on the executor, whose Future nobody reads: without this, a failure
        # would vanish without a trace.
        try:
            with self._session_maker() as session:
                NotifyOneTimeLinkReadUseCase(
                    SqlOneTimeLinkSubscriptionRepository(session),
                    self._recipient_gateway,
                    self._email_gateway,
                    self._app_base_url,
                ).execute(command)
        except Exception:  # noqa: BLE001 - courtesy email: a failure is logged, never raised into the executor
            logger.error("Failed to notify the read of one-time link %s", command.link_id, exc_info=True)
