from datetime import datetime, timezone

from vault_management_context.application.gateways import ShareRepository
from vault_management_context.domain.entities import Share

# Hard cap on the number of pending unlock shares held in memory. Legitimate
# accumulation never exceeds the vault's share count (a handful); the cap bounds
# memory against an anonymous flood on the unauthenticated /vault/unlock endpoint.
# (Deduplication is a domain concern enforced upstream in UnlockVaultUseCase.)
MAX_PENDING_SHARES = 64


class InMemoryShareRepository(ShareRepository):
    def __init__(self):
        self._shares: list[Share] = []
        self._last_share_timestamp: datetime | None = None

    def get_all(self) -> list[Share]:
        return self._shares.copy()

    def add(self, shares: list[Share]) -> None:
        added = False
        for share in shares:
            if len(self._shares) >= MAX_PENDING_SHARES:
                break  # cap: bound memory against a flood
            self._shares.append(share)
            added = True
        if added:
            self._last_share_timestamp = datetime.now(timezone.utc)

    def clear(self) -> None:
        self._shares = []
        self._last_share_timestamp = None

    def get_last_share_timestamp(self) -> datetime | None:
        return self._last_share_timestamp
