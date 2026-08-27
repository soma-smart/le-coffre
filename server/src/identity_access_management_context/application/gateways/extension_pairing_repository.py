from datetime import datetime
from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import ExtensionPairing
from identity_access_management_context.domain.value_objects import PairingUserCode


class ExtensionPairingRepository(Protocol):
    def add(self, pairing: ExtensionPairing) -> ExtensionPairing: ...

    def get_by_user_code(self, user_code: PairingUserCode) -> ExtensionPairing | None: ...

    def save(self, pairing: ExtensionPairing) -> None:
        """Persist an approval or a denial."""
        ...

    def consume(self, pairing_id: UUID, now: datetime) -> bool:
        """Mark a pairing redeemed. Returns False if it already was.

        One conditional UPDATE rather than a read-then-write: the WHERE clause
        is the concurrency guard, so two simultaneous exchanges cannot both mint
        a credential. Whichever transaction gets rowcount 1 is the single
        redeemer.
        """
        ...

    def purge_expired(self, cutoff: datetime) -> None: ...
