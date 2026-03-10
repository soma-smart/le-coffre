from datetime import datetime, timezone
from typing import List, Optional

from vault_management_context.application.gateways import ShareRepository
from vault_management_context.domain.entities import Share


class FakeShareRepository(ShareRepository):
    def __init__(self):
        self._shares: List[Share] = []
        self._last_share_timestamp: Optional[datetime] = None

    def get_all(self) -> List[Share]:
        return self._shares.copy()

    def add(self, shares: List[Share]) -> None:
        self._shares.extend(shares)
        self._last_share_timestamp = datetime.now(timezone.utc)

    def clear(self) -> None:
        self._shares = []
        self._last_share_timestamp = None

    def get_last_share_timestamp(self) -> Optional[datetime]:
        return self._last_share_timestamp
