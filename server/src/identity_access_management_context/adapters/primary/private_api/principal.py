"""Private API exposing identity resolution to other bounded contexts.

Used by the rate-limit middleware (shared_kernel) to answer "does this
access_token belong to a valid user?" without importing TokenGateway directly.

Mirrors the pattern used by UserInfoApi (sibling file).
"""

from __future__ import annotations

from uuid import UUID

from identity_access_management_context.application.gateways import TokenGateway


class PrincipalApi:
    """Private API: resolve an authenticated principal from an access token."""

    def __init__(self, token_gateway: TokenGateway) -> None:
        self._token_gateway = token_gateway

    async def resolve_user_id_from_access_token(self, access_token: str) -> UUID | None:
        """Return the UUID of the authenticated user, or None if the token is invalid/expired."""
        try:
            token = await self._token_gateway.validate_token(access_token)
        except Exception:  # noqa: BLE001 - unexpected token-layer errors treated as "not authenticated"
            return None
        if token is None:
            return None
        return token.user_id
