from datetime import datetime
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import ExtensionPairing
from identity_access_management_context.domain.value_objects import PairingUserCode


class ExtensionPairingRepository(Protocol):
    def add(self, pairing: ExtensionPairing) -> ExtensionPairing: ...

    def get_by_user_code(self, user_code: PairingUserCode) -> ExtensionPairing | None: ...

    def approve(self, pairing_id: UUID, user_id: UUID, now: datetime) -> bool:
        """Bind a still-pending pairing to a user. Returns False if it no longer is.

        Every state transition on a pairing is one conditional UPDATE whose
        WHERE clause names the state it expects to find, and the caller reads
        the rowcount. The entity's own checks run on a copy that may be stale
        by the time the write lands: an earlier version wrote every timestamp
        back from that copy, so a denial or a consumption that landed between
        the read and the write was silently erased, and one approval could mint
        two credentials.
        """
        ...

    def deny(self, pairing_id: UUID, now: datetime) -> bool:
        """Refuse a still-pending pairing. Returns False if it no longer is.

        Same guard as approve(): a denial must never lose to an approval that
        read the row a moment earlier, since denying is the way out of a
        phishing attempt.
        """
        ...

    def consume(self, pairing_id: UUID, now: datetime) -> bool:
        """Mark an approved, unexpired pairing redeemed. Returns False otherwise.

        One conditional UPDATE rather than a read-then-write: the WHERE clause
        is the concurrency guard, so two simultaneous exchanges cannot both mint
        a credential. Whichever transaction gets rowcount 1 is the single
        redeemer.
        """
        ...

    def purge_expired(self, cutoff: datetime) -> None: ...
