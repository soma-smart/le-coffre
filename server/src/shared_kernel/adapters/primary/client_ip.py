"""X-Forwarded-For-aware client IP resolution.

The rate limiter needs a correct client IP to key buckets against.  Reading
``X-Forwarded-For`` blindly lets any client forge an IP per request by setting
the header themselves, which defeats IP-based rate limiting entirely.

The rule encoded here: only trust ``X-Forwarded-For`` when the direct TCP
peer is a known proxy (``TRUSTED_PROXIES``); and within that header, only
trust the rightmost ``TRUSTED_PROXY_HOPS`` entries (each appended by our own
proxy chain), not the leftmost one (which the client originated).
"""

from __future__ import annotations

from typing import Protocol


class _HasClientAndHeaders(Protocol):
    client: object | None
    headers: dict[str, str]


def resolve_client_ip(
    request: _HasClientAndHeaders,
    *,
    trusted_proxies: set[str],
    hops: int,
) -> str:
    """Return the caller's client IP, honoring XFF only for trusted peers.

    ``trusted_proxies`` is the set of direct peer IPs whose ``X-Forwarded-For``
    header is allowed to override the peer address.  ``hops`` is the number
    of trusted proxy hops between the client and this server; we take the
    entry at position ``len(xff) - hops`` — i.e. the hop nearest us that we
    trust to have appended an authentic value.
    """
    client = getattr(request, "client", None)
    peer = getattr(client, "host", None) or "unknown"

    if hops <= 0 or peer not in trusted_proxies:
        return peer

    raw = request.headers.get("X-Forwarded-For", "")
    entries = [p.strip() for p in raw.split(",") if p.strip()]
    if len(entries) < hops:
        return peer
    return entries[-hops]
