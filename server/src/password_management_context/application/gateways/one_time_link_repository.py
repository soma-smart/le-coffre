from datetime import datetime
from typing import Protocol
from uuid import UUID

from password_management_context.domain.entities import OneTimeLink


class OneTimeLinkRepository(Protocol):
    """Repository for one-time links.

    Like the other gateways in this codebase, implementations never read the
    clock: `now` is passed in by the caller so expiry and consumption stay
    testable without monkeypatching.
    """

    def add(self, link: OneTimeLink) -> None:
        """Persist a freshly created link"""
        ...

    def get_by_id(self, link_id: UUID) -> OneTimeLink | None:
        """Fetch a link by its identifier"""
        ...

    def get_by_token_hash(self, token_hash: str) -> OneTimeLink | None:
        """Fetch a link by the hash of its token"""
        ...

    def list_for_password(self, password_id: UUID, limit: int) -> list[OneTimeLink]:
        """List at most `limit` links for a password, most recent first.

        Bounded on purpose: read and revoked links are never deleted, so an
        unbounded listing grows without end and eventually dominates both the
        HTTP response and the management UI.
        """
        ...

    def list_active_for_password(self, password_id: UUID, now: datetime, limit: int) -> list[OneTimeLink]:
        """List the still-redeemable links, most recent first.

        Filtered in the query rather than by trimming a page of recent links: an
        active link can sit behind any number of newer spent ones, and slicing
        the recent page would silently hide it from the owner who needs to
        revoke it.
        """
        ...

    def count_for_password(self, password_id: UUID) -> int:
        """Total number of links issued for a password, ignoring any limit"""
        ...

    def count_active_for_password(self, password_id: UUID, now: datetime) -> int:
        """How many links are still redeemable: unread, unrevoked and unexpired"""
        ...

    def count_all(self) -> int:
        """Total number of links ever issued, across every password"""
        ...

    def list_all(self, now: datetime, include_inactive: bool, limit: int) -> list[OneTimeLink]:
        """Vault-wide listing, most recent first, redeemable ones only by default.

        Filtered in the query rather than by trimming a page: an old active link
        can sit behind any number of newer spent ones, and slicing first would
        hide it from the admin who needs to revoke it.
        """
        ...

    def count_all_matching(self, now: datetime, include_inactive: bool) -> int:
        """How many links the equivalent list_all would have without its limit"""
        ...

    def list_for_creator(
        self, created_by_user_id: UUID, now: datetime, include_inactive: bool, limit: int
    ) -> list[OneTimeLink]:
        """Same listing, restricted to the links one user issued"""
        ...

    def count_for_creator(self, created_by_user_id: UUID, now: datetime, include_inactive: bool) -> int:
        """How many links the equivalent list_for_creator would have without its limit"""
        ...

    def revoke_all_for_creator(self, created_by_user_id: UUID, now: datetime) -> int:
        """Revoke every still-redeemable link a user issued, returning the count.

        One conditional UPDATE, so links already read keep their read timestamp:
        that timestamp is audit data and must never be overwritten by a revoke.
        """
        ...

    def count_active_all(self, now: datetime) -> int:
        """How many links are still redeemable, across every password"""
        ...

    def consume(self, link_id: UUID, now: datetime) -> bool:
        """Atomically mark the link as read.

        Returns True if this call is the one that consumed it, False if it was
        already read or revoked. Implementations MUST make this a single
        conditional write: checking then writing would let two concurrent
        requests both read the secret, and the link would not be single-use.
        """
        ...

    def revoke(self, link_id: UUID, now: datetime) -> bool:
        """Atomically mark the link as revoked.

        Returns False when the link was already read or revoked, so a revoke
        never overwrites the audit trail of an actual read.
        """
        ...

    def delete_for_password(self, password_id: UUID) -> None:
        """Drop every link of a password, used when the password itself goes away"""
        ...
