import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from shared_kernel.application.gateways import TimeGateway
from vault_management_context.adapters.secondary import SqlShareLinkRepository
from vault_management_context.application.use_cases import PurgeExpiredShareLinksUseCase

logger = logging.getLogger(__name__)

# Links live 48 hours: an expired one lingering up to an hour more is harmless,
# it can no longer be retrieved anyway.
PURGE_INTERVAL_SECONDS = 3600
# How often to check again while the database migrations are still running.
NOT_READY_RETRY_SECONDS = 5


class ExpiredShareLinkPurgeJob:
    """Purges expired share links on a timer, for the life of the app.

    Every run is an idempotent DELETE, so several replicas running it side by
    side is harmless.
    """

    def __init__(
        self,
        session_maker: sessionmaker[Session],
        time_gateway: TimeGateway,
        interval_seconds: float = PURGE_INTERVAL_SECONDS,
        not_ready_retry_seconds: float = NOT_READY_RETRY_SECONDS,
    ) -> None:
        self._session_maker = session_maker
        self._time_gateway = time_gateway
        self._interval_seconds = interval_seconds
        self._not_ready_retry_seconds = not_ready_retry_seconds

    def run_once(self) -> None:
        with self._session_maker() as session:
            PurgeExpiredShareLinksUseCase(SqlShareLinkRepository(session), self._time_gateway).execute()

    async def run_forever(self, is_ready: Callable[[], bool]) -> None:
        """Purge now and then every interval, once the schema is in place."""
        while True:
            if not is_ready():
                await asyncio.sleep(self._not_ready_retry_seconds)
                continue
            try:
                await asyncio.to_thread(self.run_once)
            except Exception:
                # A failed run must not stop the next ones
                logger.exception("Purging expired share links failed")
            await asyncio.sleep(self._interval_seconds)
