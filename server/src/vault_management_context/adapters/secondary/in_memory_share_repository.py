from datetime import datetime, timezone

from vault_management_context.application.gateways import ShareRepository
from vault_management_context.domain.entities import Share


class InMemoryShareRepository(ShareRepository):
    def __init__(self):
        self._shares: list[Share] = []
        self._last_share_timestamp: datetime | None = None

    def get_all(self) -> list[Share]:
        return self._shares.copy()

    def add(self, shares: list[Share]) -> None:
        self._shares.extend(shares)
        self._last_share_timestamp = datetime.now(timezone.utc)

    def clear(self) -> None:
        self._shares = []
        self._last_share_timestamp = None

    def get_last_share_timestamp(self) -> datetime | None:
        return self._last_share_timestamp
