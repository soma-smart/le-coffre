from datetime import datetime
from uuid import UUID

from sqlmodel import Session, col, delete, select

from notification_context.adapters.secondary.sql.one_time_link_subscription_model import (
    OneTimeLinkSubscriptionTable,
)
from notification_context.application.gateways import OneTimeLinkSubscriptionRepository
from notification_context.domain.entities import OneTimeLinkSubscription
from shared_kernel.adapters.secondary.sql.sql_base_repository import SQLBaseRepository
from shared_kernel.utils import as_utc, to_naive_utc


def _to_entity(row: OneTimeLinkSubscriptionTable) -> OneTimeLinkSubscription:
    return OneTimeLinkSubscription(
        link_id=row.link_id,
        user_id=row.user_id,
        expires_at=as_utc(row.expires_at),  # type: ignore[arg-type]
        notify_on_read=row.notify_on_read,
        notify_on_expiry=row.notify_on_expiry,
    )


class SqlOneTimeLinkSubscriptionRepository(SQLBaseRepository, OneTimeLinkSubscriptionRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def get(self, link_id: UUID) -> OneTimeLinkSubscription | None:
        row = self._session.get(OneTimeLinkSubscriptionTable, link_id)
        return _to_entity(row) if row is not None else None

    def save(self, subscription: OneTimeLinkSubscription) -> None:
        row = self._session.get(OneTimeLinkSubscriptionTable, subscription.link_id)
        if row is None:
            row = OneTimeLinkSubscriptionTable(link_id=subscription.link_id, user_id=subscription.user_id)
        row.user_id = subscription.user_id
        row.expires_at = to_naive_utc(subscription.expires_at)  # type: ignore[assignment]
        row.notify_on_read = subscription.notify_on_read
        row.notify_on_expiry = subscription.notify_on_expiry
        self._session.add(row)
        self.commit()

    def remove(self, link_id: UUID) -> bool:
        # One DELETE, not a read-then-delete: the row is the claim. Whichever
        # transaction deletes it gets rowcount 1 and sends the email; the others get 0.
        statement = delete(OneTimeLinkSubscriptionTable).where(col(OneTimeLinkSubscriptionTable.link_id) == link_id)
        result = self._session.exec(statement)  # type: ignore[call-overload]
        self.commit()
        return result.rowcount == 1

    def list_expired(self, now: datetime, limit: int) -> list[OneTimeLinkSubscription]:
        statement = (
            select(OneTimeLinkSubscriptionTable)
            .where(col(OneTimeLinkSubscriptionTable.expires_at) <= to_naive_utc(now))
            .order_by(col(OneTimeLinkSubscriptionTable.expires_at).asc())
            .limit(limit)
        )
        return [_to_entity(row) for row in self._session.exec(statement).all()]
