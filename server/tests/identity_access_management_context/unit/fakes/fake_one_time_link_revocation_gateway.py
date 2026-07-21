from uuid import UUID

from identity_access_management_context.application.gateways import (
    OneTimeLinkRevocationGateway,
)


class FakeOneTimeLinkRevocationGateway(OneTimeLinkRevocationGateway):
    def __init__(self):
        self.revoked_for: list[UUID] = []
        self._counts: dict[UUID, int] = {}

    def revoke_all_for_user(self, user_id: UUID) -> int:
        self.revoked_for.append(user_id)
        return self._counts.get(user_id, 0)

    # ── Test-only helpers ──────────────────────────────────────────
    def set_link_count(self, user_id: UUID, count: int) -> None:
        """Pretend this user has `count` live links waiting to be cut."""
        self._counts[user_id] = count
