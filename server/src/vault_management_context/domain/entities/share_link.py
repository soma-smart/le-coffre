from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from vault_management_context.domain.exceptions import ShareLinkUnusableError

# Long enough for every custodian to be reached across a weekend gap, short
# enough that an unopened link does not linger as a standing grant. The setup
# does not wait for retrieval: an expired link means the share is lost.
SHARE_LINK_LIFETIME = timedelta(hours=48)


@dataclass
class ShareLink:
    """A single-use, time-limited link handing one Shamir share to its custodian.

    `sealed_share` is the share encrypted under a key derived from the link
    token, which only exists in the URL fragment: the server can hand the
    ciphertext out but never open it. The link is deleted as soon as it is
    retrieved or expires.
    """

    id: UUID
    setup_id: str
    share_index: int
    lookup_hash: str
    sealed_share: str
    created_at: datetime
    expires_at: datetime

    @classmethod
    def create(
        cls,
        setup_id: str,
        share_index: int,
        lookup_hash: str,
        sealed_share: str,
        now: datetime,
    ) -> "ShareLink":
        return cls(
            id=uuid4(),
            setup_id=setup_id,
            share_index=share_index,
            lookup_hash=lookup_hash,
            sealed_share=sealed_share,
            created_at=now,
            expires_at=now + SHARE_LINK_LIFETIME,
        )

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def ensure_not_expired(self, now: datetime) -> None:
        """Same error as for an unknown link: an anonymous caller must not learn
        whether a link exists."""
        if self.is_expired(now):
            raise ShareLinkUnusableError()
