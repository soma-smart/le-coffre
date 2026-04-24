"""X-Forwarded-For-aware client IP resolution.

Rate limiting needs a correct client IP to key buckets against.  Reading
``X-Forwarded-For`` blindly lets any client forge an IP per request by setting
the header themselves, which defeats IP-based rate limiting entirely.

The rule encoded here: only trust ``X-Forwarded-For`` when the direct TCP
peer is a known proxy (``trusted_proxies``); and within that header, only
trust the rightmost ``hops`` entries — each one was appended by a link in the
proxy chain we control, so the entry at position ``len(xff) - hops`` is the
nearest hop we trust to have written an authentic value.
"""

from __future__ import annotations

import logging
from typing import Mapping, Protocol

logger = logging.getLogger(__name__)

# Module-level latch: a misconfigured proxy would otherwise fire one WARNING
# per request (hundreds per minute during an outage) before the 'unknown'
# bucket's 429s cap volume. Emit once per process — subsequent occurrences
# are still observable via the shared-bucket 429s, and the first warning is
# what SRE needs to start diagnosing. Module reload (e.g. test restart)
# resets the latch, which is the right scope.
_missing_peer_warned = False


class _HasClientAndHeaders(Protocol):
    client: object | None
    # Starlette's ``Request.headers`` is a ``Headers`` mapping (case-insensitive,
    # multi-value-aware), not a plain ``dict[str, str]``.  We only need ``.get``
    # with a string key returning a string, so a read-only ``Mapping`` describes
    # exactly the surface we depend on without over-constraining the shape.
    headers: Mapping[str, str]


def resolve_client_ip(
    request: _HasClientAndHeaders,
    *,
    trusted_proxies: set[str],
    hops: int,
) -> str:
    """Return the caller's client IP, honoring XFF only for trusted peers."""
    client = getattr(request, "client", None)
    peer = getattr(client, "host", None)
    if peer is None:
        # No resolvable TCP peer: shared `unknown` bucket (small blast radius),
        # usually a misconfigured reverse proxy. Latched WARNING (see module).
        global _missing_peer_warned
        if not _missing_peer_warned:
            logger.warning(
                "resolve_client_ip: request has no TCP peer; keying to the shared 'unknown' bucket. "
                "This usually indicates a misconfigured reverse proxy. "
                "Subsequent occurrences suppressed for the life of this process."
            )
            _missing_peer_warned = True
        peer = "unknown"

    if hops <= 0 or peer not in trusted_proxies:
        return peer

    raw = request.headers.get("X-Forwarded-For", "")
    entries = [p.strip() for p in raw.split(",") if p.strip()]
    if len(entries) < hops:
        return peer
    return entries[-hops]
