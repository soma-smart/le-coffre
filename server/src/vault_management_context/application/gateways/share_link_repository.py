from datetime import datetime
from typing import Protocol
from uuid import UUID

from vault_management_context.domain.entities import ShareLink


class ShareLinkRepository(Protocol):
    """Store for the links that hand each Shamir share to its custodian."""

    def replace_all(self, links: list[ShareLink]) -> None:
        """Drop every existing link and store these instead.

        A re-setup generates a new master key, so the links of the previous
        attempt carry shares that open nothing and must not survive it.
        """
        ...

    def get_by_lookup_hash(self, lookup_hash: str) -> ShareLink | None: ...

    def consume(self, link_id: UUID, now: datetime) -> bool:
        """Delete the link if it has not expired, in one conditional write.

        Returns True only for the caller that actually deleted it, so two
        concurrent requests cannot both walk away with the share.
        """
        ...

    def purge_expired(self, now: datetime) -> None:
        """Delete every link past its expiry."""
        ...
