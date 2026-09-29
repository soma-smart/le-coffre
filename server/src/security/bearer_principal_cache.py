"""Short-lived memory of which user an extension bearer token belongs to.

Exists for two reasons, in this order.

**It keeps a rate-limit guard from becoming an attack.** ``RateLimitMiddleware``
budgets how many *failed* token lookups one address may cause, so a caller
guessing tokens cannot buy unlimited queries. That budget is spent before the
lookup tells us whether this particular token is junk, so without a cache an
attacker who exhausts it from a shared address also stops their colleagues'
genuine extensions from being recognised, dropping them into the anonymous
bucket the attacker has just filled. A token seen working recently skips the
budget entirely, so the guard can no longer be turned against its own users.

**It removes a query from the hot path.** Before this, every extension request
cost a connection checkout and a SELECT purely to decide which bucket to charge.
Now it costs one per token per TTL.

What is cached is a *rate-limit bucket choice*, never an authorization decision:
``get_current_principal`` still resolves the credential against the database on
every single request. A token revoked mid-TTL therefore keeps its per-user
bucket for at most ``ttl_seconds`` and is refused by the route regardless, which
is why a short TTL and no invalidation hook are enough.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta

DEFAULT_TTL_SECONDS = 60

# A paired extension holds at most MAX_ACTIVE_TOKENS_PER_USER credentials, so
# in normal use this holds one entry per connected device. The bound exists for
# the abnormal case, and evicting the whole map is deliberate: entries are worth
# a single database lookup each, so a cheap and obviously correct eviction beats
# an LRU whose bookkeeping would cost more than what it protects.
MAX_ENTRIES = 10_000


class BearerPrincipalCache:
    """Maps a token hash to its user id for a short while. Thread-safe."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._entries: dict[str, tuple[str, datetime]] = {}
        self._lock = threading.Lock()

    def get(self, token_hash: str, now: datetime) -> str | None:
        """The user id this token resolved to, or None if unknown or stale."""
        with self._lock:
            entry = self._entries.get(token_hash)
            if entry is None:
                return None
            user_id, stored_at = entry
            if now - stored_at >= self._ttl:
                del self._entries[token_hash]
                return None
            return user_id

    def put(self, token_hash: str, user_id: str, now: datetime) -> None:
        """Record a lookup that succeeded. Only ever called with a real token."""
        with self._lock:
            if len(self._entries) >= MAX_ENTRIES and token_hash not in self._entries:
                self._entries.clear()
            self._entries[token_hash] = (user_id, now)

    def clear(self) -> None:
        """Testing helper."""
        with self._lock:
            self._entries.clear()
