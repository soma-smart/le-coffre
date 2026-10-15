import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

# Long enough for every custodian to be reached across a weekend gap, short
# enough that an unopened link does not linger as a standing grant. The setup
# does not wait for retrieval: an expired link means the share is lost.
SHARE_LINK_LIFETIME = timedelta(hours=48)

# After its first opening, a link can be opened again for this long, until the
# custodian confirms they saved the share: a dropped response, a closed tab or a
# share that failed to open must not cost the share. Short, because every
# reopening is also a chance for someone else holding the link.
SHARE_LINK_REOPEN_WINDOW = timedelta(minutes=15)


@dataclass
class ShareLink:
    """A time-limited link handing one Shamir share to its custodian.

    `sealed_share` is the share encrypted under a key derived from the link
    token, which only exists in the URL fragment: the server can hand the
    ciphertext out but never open it.

    Lifecycle: pending until first opened; then delivered, and openable again
    until `reopenable_until`; deleted once the custodian acknowledges it, or
    purged once expired or past its reopen window.

    `ack_hash` is the SHA-256 of a second key derived from the token: only the
    token holder can produce the acknowledgement, not someone who merely knows
    the lookup hash (which the database holds).
    """

    id: UUID
    setup_id: str
    share_index: int
    lookup_hash: str
    ack_hash: str
    sealed_share: str
    created_at: datetime
    expires_at: datetime
    delivered_at: datetime | None = None
    reopenable_until: datetime | None = None

    @classmethod
    def create(
        cls,
        setup_id: str,
        share_index: int,
        lookup_hash: str,
        ack_hash: str,
        sealed_share: str,
        now: datetime,
    ) -> "ShareLink":
        return cls(
            id=uuid4(),
            setup_id=setup_id,
            share_index=share_index,
            lookup_hash=lookup_hash,
            ack_hash=ack_hash,
            sealed_share=sealed_share,
            created_at=now,
            expires_at=now + SHARE_LINK_LIFETIME,
        )

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def is_delivered(self) -> bool:
        return self.delivered_at is not None

    def can_be_delivered(self, now: datetime) -> bool:
        if self.is_expired(now):
            return False
        return self.reopenable_until is None or now < self.reopenable_until

    def reopen_deadline(self, now: datetime) -> datetime:
        """End of the reopen window a first opening at `now` starts.

        Never past the link's own expiry: the custodian is shown this deadline,
        and a later reopening refused before it would read as someone else
        having taken the share.
        """
        return min(now + SHARE_LINK_REOPEN_WINDOW, self.expires_at)

    def can_be_acknowledged(self, now: datetime) -> bool:
        """Only while it could still be delivered: past that, the link closed on
        its own, and the audit trail must not show a custodian closing it."""
        return self.is_delivered() and self.can_be_delivered(now)

    def is_purgeable(self, now: datetime) -> bool:
        return not self.can_be_delivered(now)

    def accepts_ack(self, ack_key: bytes) -> bool:
        return hmac.compare_digest(hashlib.sha256(ack_key).hexdigest(), self.ack_hash)
