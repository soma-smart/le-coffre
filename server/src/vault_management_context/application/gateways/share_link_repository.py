from datetime import datetime
from typing import Protocol
from uuid import UUID

from vault_management_context.domain.entities import ShareLink
from vault_management_context.domain.value_objects import ShareLinkDelivery


class ShareLinkRepository(Protocol):
    """Store for the links that hand each Shamir share to its custodian."""

    def replace_all(self, links: list[ShareLink]) -> None:
        """Drop every existing link and store these instead.

        A re-setup generates a new master key, so the links of the previous
        attempt carry shares that open nothing and must not survive it.
        """
        ...

    def get_by_lookup_hash(self, lookup_hash: str) -> ShareLink | None: ...

    # The conditions below restate ShareLink's rules (can_be_delivered,
    # can_be_acknowledged, is_purgeable) as conditional writes: the use cases
    # decide with the entity, and these writes only guard against a concurrent
    # request changing the row in between. Both implementations are held to
    # the same behaviour by test_share_link_repository_contract.py.

    def deliver(self, link_id: UUID, now: datetime, reopenable_until: datetime) -> ShareLinkDelivery | None:
        """Record that the link is being handed out, if it still can be.

        The first delivery starts the reopen window, ending at
        `reopenable_until` (see ShareLink.reopen_deadline), in one conditional
        write so two concurrent first openings cannot both start it: the loser
        sees a reopening. Returns None if the link is gone, expired or past its
        window.
        """
        ...

    def remove_delivered(self, link_id: UUID, now: datetime) -> bool:
        """Delete the link once acknowledged: only if delivered, and still
        within its reopen window and its lifetime.

        Returns True only for the caller that actually deleted it.
        """
        ...

    def purge_expired(self, now: datetime) -> None:
        """Delete every link past its expiry or its reopen window."""
        ...
