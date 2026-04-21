"""PrincipalResolver gateway.

The rate-limit middleware needs to know "who is this caller?" to key the
per-user bucket.  That answer is owned by identity_access_management_context
(access-token validation), but we don't want the middleware importing IAM
directly — the project's cross-context rule is to go through a private API.

This Protocol is the shared-kernel-side of that seam.  IAM implements it via
adapters/secondary/private_api/iam_principal_resolver.py, which wraps
IAM's primary-api PrincipalApi.  The middleware depends only on this Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class Principal:
    """The identity we'll key rate-limiting against for this request."""

    kind: Literal["user", "ip"]
    id: str


class PrincipalResolver(Protocol):
    async def resolve(self, access_token: str | None, fallback_ip: str) -> Principal:
        """Return Principal('user', user_id) if the token decodes, else Principal('ip', fallback_ip)."""
        ...
