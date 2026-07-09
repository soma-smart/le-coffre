import logging
from datetime import datetime, timezone

from vault_management_context.application.gateways import ShareRepository
from vault_management_context.domain.entities import Share

logger = logging.getLogger(__name__)

# Hard cap on the number of pending unlock shares held in memory. Legitimate
# accumulation never exceeds the vault's share count (a handful); the cap bounds
# memory against an anonymous flood on the unauthenticated /vault/unlock endpoint.
# (Deduplication is a domain concern enforced upstream in UnlockVaultUseCase.)
# When full, newly submitted shares are dropped rather than evicting existing ones:
# eviction would let an attacker flush already-submitted legitimate shares.
MAX_PENDING_SHARES = 64


class InMemoryShareRepository(ShareRepository):
    def __init__(self):
        self._shares: list[Share] = []
        self._last_share_timestamp: datetime | None = None

    def get_all(self) -> list[Share]:
        return self._shares.copy()

    def add(self, shares: list[Share]) -> None:
        accepted = 0
        for share in shares:
            if len(self._shares) >= MAX_PENDING_SHARES:
                break  # cap: bound memory against a flood
            self._shares.append(share)
            accepted += 1

        dropped = len(shares) - accepted
        if dropped:
            # Surface the (rare) cap hit — likely a share-pool flood. An operator
            # can clear the pending shares to let legitimate submissions through.
            logger.warning(
                "Pending unlock-share pool at capacity (%d); dropped %d submitted share(s). "
                "Possible flood on /vault/unlock — clear pending shares to recover.",
                MAX_PENDING_SHARES,
                dropped,
            )

        if accepted:
            self._last_share_timestamp = datetime.now(timezone.utc)

    def clear(self) -> None:
        self._shares = []
        self._last_share_timestamp = None

    def get_last_share_timestamp(self) -> datetime | None:
        return self._last_share_timestamp
