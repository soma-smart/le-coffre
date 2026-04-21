"""shared_kernel-side adapter that implements PrincipalResolver via IAM's private PrincipalApi."""

from __future__ import annotations

import logging

from identity_access_management_context.adapters.primary.private_api.principal import (
    PrincipalApi,
)
from shared_kernel.application.gateways import Principal, PrincipalResolver

logger = logging.getLogger(__name__)


class IamPrincipalResolver(PrincipalResolver):
    def __init__(self, principal_api: PrincipalApi) -> None:
        self._principal_api = principal_api

    async def resolve(self, access_token: str | None, fallback_ip: str) -> Principal:
        if not access_token:
            return Principal(kind="ip", id=fallback_ip)
        try:
            user_id = await self._principal_api.resolve_user_id_from_access_token(access_token)
        except Exception:  # noqa: BLE001
            logger.debug("Principal resolution failed; falling back to IP keying", exc_info=True)
            user_id = None
        if user_id is None:
            return Principal(kind="ip", id=fallback_ip)
        return Principal(kind="user", id=str(user_id))
