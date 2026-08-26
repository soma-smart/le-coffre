from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from identity_access_management_context.domain.exceptions import (
    ExtensionTokenExpiredError,
    ExtensionTokenRevokedError,
)
from identity_access_management_context.domain.value_objects.extension_token_secret import (
    ExtensionTokenSecret,
)

# Each active token is an independent, long-lived read grant living in a browser
# profile. Capping how many can exist at once bounds that exposure and makes an
# accidental burst of pairings visible. Revoked and expired tokens free their
# slot, so this never blocks someone who re-pairs over time.
MAX_ACTIVE_TOKENS_PER_USER = 5


@dataclass
class ExtensionToken:
    """A long-lived, read-only credential held by one paired browser extension.

    Rows are kept after revocation or expiry so the pairing stays auditable,
    which is why "revoked" is a timestamp rather than a deletion.
    """

    id: UUID
    user_id: UUID
    token_hash: str
    device_name: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_from_ip: str | None = None

    @classmethod
    def create(
        cls,
        user_id: UUID,
        secret: ExtensionTokenSecret,
        device_name: str,
        lifetime: timedelta,
        now: datetime,
        created_from_ip: str | None = None,
    ) -> "ExtensionToken":
        return cls(
            id=uuid4(),
            user_id=user_id,
            token_hash=secret.hashed(),
            device_name=device_name,
            created_at=now,
            expires_at=now + lifetime,
            last_used_at=None,
            revoked_at=None,
            created_from_ip=created_from_ip,
        )

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_active(self, now: datetime) -> bool:
        return not self.is_revoked() and not self.is_expired(now)

    def ensure_usable(self, now: datetime) -> None:
        """Raise the matching domain error unless the credential still works.

        Every arm carries the same message on purpose, see
        InvalidExtensionTokenError. The distinct types exist so the caller can
        log which one fired without leaking it to the client.
        """
        if self.is_revoked():
            raise ExtensionTokenRevokedError()
        if self.is_expired(now):
            raise ExtensionTokenExpiredError()

    def revoke(self, now: datetime) -> None:
        # Idempotent: re-revoking keeps the original timestamp, so the audit
        # trail records when access actually stopped rather than when someone
        # last clicked the button.
        if self.revoked_at is None:
            self.revoked_at = now
