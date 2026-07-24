from typing import Protocol
from uuid import UUID


class OneTimeLinkRevocationGateway(Protocol):
    def revoke_all_for_user(self, user_id: UUID) -> int:
        """Revoke every still-redeemable one-time link issued by this user"""
        ...
