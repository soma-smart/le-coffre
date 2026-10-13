from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from password_management_context.domain.exceptions import (
    OneTimeLinkAlreadyUsedError,
    OneTimeLinkExpiredError,
    OneTimeLinkRevokedError,
)
from password_management_context.domain.value_objects import (
    OneTimeLinkLifetime,
    OneTimeLinkToken,
)

# Every active link is a live, unauthenticated read grant on the same secret,
# and each has to be revoked individually. Capping how many can be outstanding
# at once keeps that exposure bounded and makes an accidental burst of clicks
# visible immediately. Read, revoked and expired links free their slot, so this
# never blocks an owner who keeps sharing over time.
MAX_ACTIVE_LINKS_PER_PASSWORD = 5


@dataclass
class OneTimeLink:
    """A single-use, time-limited grant to read one password without logging in.

    Rows are kept after consumption or revocation so the read stays auditable,
    which is why "used" is a timestamp rather than a deletion.
    """

    id: UUID
    password_id: UUID
    token_hash: str
    created_by_user_id: UUID
    created_at: datetime
    expires_at: datetime
    read_at: datetime | None = None
    revoked_at: datetime | None = None
    # The creator's opt-ins, chosen once at creation. They are stored on the link
    # (not as a user preference) because the choice is about this one link.
    notify_on_read: bool = False
    notify_on_expiry: bool = False
    # Set once, atomically, by the expiry sweep: the claim that makes the expiry
    # notification exactly-once across replicas.
    expiry_notified_at: datetime | None = None

    @classmethod
    def create(
        cls,
        password_id: UUID,
        created_by_user_id: UUID,
        token: OneTimeLinkToken,
        lifetime: OneTimeLinkLifetime,
        now: datetime,
        notify_on_read: bool = False,
        notify_on_expiry: bool = False,
    ) -> "OneTimeLink":
        return cls(
            id=uuid4(),
            password_id=password_id,
            token_hash=token.hashed(),
            created_by_user_id=created_by_user_id,
            created_at=now,
            expires_at=now + lifetime.as_timedelta(),
            read_at=None,
            revoked_at=None,
            notify_on_read=notify_on_read,
            notify_on_expiry=notify_on_expiry,
            expiry_notified_at=None,
        )

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def is_consumed(self) -> bool:
        return self.read_at is not None

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def ensure_consumable(self, now: datetime) -> None:
        """Raise the matching domain error unless the link can still be read."""
        if self.is_revoked():
            raise OneTimeLinkRevokedError()
        if self.is_consumed():
            raise OneTimeLinkAlreadyUsedError()
        if self.is_expired(now):
            raise OneTimeLinkExpiredError()

    def mark_read(self, now: datetime) -> None:
        self.read_at = now

    def mark_revoked(self, now: datetime) -> None:
        self.revoked_at = now

    def mark_expiry_notified(self, now: datetime) -> None:
        self.expiry_notified_at = now
