from datetime import datetime
from typing import Protocol
from uuid import UUID

from notification_context.domain.entities import OneTimeLinkSubscription


class OneTimeLinkSubscriptionRepository(Protocol):
    """Repository for one-time link subscriptions.

    Implementations never read the clock: `now` is passed in by the caller.
    """

    def get(self, link_id: UUID) -> OneTimeLinkSubscription | None: ...

    def save(self, subscription: OneTimeLinkSubscription) -> None:
        """Insert or replace the subscription of subscription.link_id"""
        ...

    def remove(self, link_id: UUID) -> bool:
        """Atomically delete the subscription.

        Returns True for the single caller that deleted it, False if it was already
        gone. Whoever gets True is the one that emails the creator: implementations
        MUST make this one conditional write, so that a read and the expiry sweep, or
        several replicas sweeping at once, never both send an email for the same link.
        """
        ...

    def list_expired(self, now: datetime, limit: int) -> list[OneTimeLinkSubscription]:
        """At most `limit` subscriptions whose link has expired, oldest expiry first"""
        ...
