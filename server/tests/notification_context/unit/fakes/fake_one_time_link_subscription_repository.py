from datetime import datetime
from uuid import UUID

from notification_context.domain.entities import OneTimeLinkSubscription


class FakeOneTimeLinkSubscriptionRepository:
    def __init__(self):
        self._subscriptions: dict[UUID, OneTimeLinkSubscription] = {}

    def get(self, link_id: UUID) -> OneTimeLinkSubscription | None:
        return self._subscriptions.get(link_id)

    def save(self, subscription: OneTimeLinkSubscription) -> None:
        self._subscriptions[subscription.link_id] = subscription

    def remove(self, link_id: UUID) -> bool:
        return self._subscriptions.pop(link_id, None) is not None

    def list_expired(self, now: datetime, limit: int) -> list[OneTimeLinkSubscription]:
        expired = sorted((s for s in self._subscriptions.values() if s.expires_at <= now), key=lambda s: s.expires_at)
        return expired[:limit]
