import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from vault_management_context.application.gateways import ShareRepository
from vault_management_context.domain.entities import Share
from vault_management_context.domain.value_objects import UnlockSessionId

logger = logging.getLogger(__name__)

# Hard cap on the number of pending unlock shares held in memory for one session.
# Legitimate accumulation never exceeds the vault's share count (a handful); the cap
# bounds memory against an anonymous flood on the unauthenticated /vault/unlock endpoint.
# (Deduplication is a domain concern enforced upstream in UnlockVaultUseCase.)
# When full, newly submitted shares are dropped rather than evicting existing ones:
# eviction would let an attacker flush already-submitted legitimate shares.
MAX_PENDING_SHARES_PER_SESSION = 64

# Hard cap on the number of concurrent unlock sessions. Legitimately there is one,
# maybe a few abandoned ones. When full, the least recently active session is evicted:
# refusing new sessions instead would let a flood block every unlock until a restart.
MAX_PENDING_SESSIONS = 64


@dataclass
class _PendingSession:
    shares: list[Share] = field(default_factory=list)
    last_share_timestamp: datetime | None = None


class InMemoryShareRepository(ShareRepository):
    def __init__(self):
        # Ordered from least to most recently active, for eviction.
        self._sessions: OrderedDict[UnlockSessionId, _PendingSession] = OrderedDict()

    def get_all(self, session_id: UnlockSessionId) -> list[Share]:
        session = self._sessions.get(session_id)
        return session.shares.copy() if session else []

    def add(self, session_id: UnlockSessionId, shares: list[Share]) -> None:
        if not shares:
            return

        session = self._sessions.get(session_id)
        if session is None:
            session = self._open_session(session_id)

        accepted = 0
        for share in shares:
            if len(session.shares) >= MAX_PENDING_SHARES_PER_SESSION:
                break  # cap: bound memory against a flood
            session.shares.append(share)
            accepted += 1

        dropped = len(shares) - accepted
        if dropped:
            # Surface the (rare) cap hit — likely a share-pool flood. The share
            # holders can start over with a new unlock session.
            logger.warning(
                "Pending unlock-share pool of a session at capacity (%d); dropped %d submitted share(s). "
                "Possible flood on /vault/unlock — start a new unlock session to recover.",
                MAX_PENDING_SHARES_PER_SESSION,
                dropped,
            )

        if accepted:
            session.last_share_timestamp = datetime.now(timezone.utc)
            self._sessions.move_to_end(session_id)

    def clear(self) -> None:
        self._sessions.clear()

    def get_last_share_timestamp(self, session_id: UnlockSessionId) -> datetime | None:
        session = self._sessions.get(session_id)
        return session.last_share_timestamp if session else None

    def _open_session(self, session_id: UnlockSessionId) -> _PendingSession:
        if len(self._sessions) >= MAX_PENDING_SESSIONS:
            self._sessions.popitem(last=False)
            logger.warning(
                "Too many pending unlock sessions (%d); evicted the least recently active one. "
                "Possible flood on /vault/unlock.",
                MAX_PENDING_SESSIONS,
            )
        session = _PendingSession()
        self._sessions[session_id] = session
        return session
