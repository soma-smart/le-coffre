from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from identity_access_management_context.domain.exceptions import (
    ExtensionPairingAlreadyResolvedError,
    ExtensionPairingDeniedError,
    ExtensionPairingExpiredError,
    ExtensionPairingNotApprovedError,
    InvalidPkceVerifierError,
)
from identity_access_management_context.domain.value_objects.pairing_user_code import (
    PairingUserCode,
)
from identity_access_management_context.domain.value_objects.pkce_challenge import (
    PkceChallenge,
    PkceVerifier,
)


@dataclass
class ExtensionPairing:
    """An in-flight request to connect one browser extension to one account.

    Deliberately a separate entity from ExtensionToken rather than a "pending"
    state on it: a pending or denied pairing must never occupy a row in the
    credential table, so that "a row exists in ExtensionToken" always means "a
    credential was actually issued". Any future code that reads existence as
    validity is then correct by construction.

    Rows are kept after resolution for audit, like OneTimeLink.
    """

    id: UUID
    user_code: PairingUserCode
    code_challenge: PkceChallenge
    device_name: str
    created_at: datetime
    expires_at: datetime
    approved_at: datetime | None = None
    approved_by_user_id: UUID | None = None
    denied_at: datetime | None = None
    consumed_at: datetime | None = None
    created_from_ip: str | None = None

    @classmethod
    def create(
        cls,
        user_code: PairingUserCode,
        code_challenge: PkceChallenge,
        device_name: str,
        lifetime: timedelta,
        now: datetime,
        created_from_ip: str | None = None,
    ) -> "ExtensionPairing":
        return cls(
            id=uuid4(),
            user_code=user_code,
            code_challenge=code_challenge,
            device_name=device_name,
            created_at=now,
            expires_at=now + lifetime,
            created_from_ip=created_from_ip,
        )

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at

    def is_resolved(self) -> bool:
        return self.approved_at is not None or self.denied_at is not None

    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def ensure_resolvable(self, now: datetime) -> None:
        """Raise unless this pairing can still be approved or denied."""
        if self.is_resolved() or self.is_consumed():
            raise ExtensionPairingAlreadyResolvedError()
        if self.is_expired(now):
            raise ExtensionPairingExpiredError()

    def approve(self, user_id: UUID, now: datetime) -> None:
        self.ensure_resolvable(now)
        self.approved_at = now
        self.approved_by_user_id = user_id

    def deny(self, now: datetime) -> None:
        self.ensure_resolvable(now)
        self.denied_at = now

    def ensure_exchangeable(self, verifier: PkceVerifier, now: datetime) -> UUID:
        """Validate an exchange attempt and return the approving user's id.

        Order matters. The verifier is checked *first*, before expiry, approval
        or denial: every other outcome is only disclosed to a caller who has
        already proved it owns this pairing. That is what makes it safe for the
        exchange endpoint to distinguish "still pending" from "gone", the
        distinction is not an oracle for anyone else.
        """
        if not self.code_challenge.matches(verifier):
            raise InvalidPkceVerifierError()
        if self.is_consumed():
            raise ExtensionPairingAlreadyResolvedError()
        if self.denied_at is not None:
            raise ExtensionPairingDeniedError()
        if self.is_expired(now):
            raise ExtensionPairingExpiredError()
        if self.approved_at is None or self.approved_by_user_id is None:
            raise ExtensionPairingNotApprovedError()
        return self.approved_by_user_id

    def mark_consumed(self, now: datetime) -> None:
        self.consumed_at = now
