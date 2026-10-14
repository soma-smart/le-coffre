from dataclasses import replace
from datetime import datetime
from uuid import UUID

from identity_access_management_context.domain.entities import ExtensionPairing
from identity_access_management_context.domain.value_objects import PairingUserCode


class FakeExtensionPairingRepository:
    def __init__(self):
        self.pairings: dict[UUID, ExtensionPairing] = {}
        self.purge_cutoffs: list[datetime] = []

    def add(self, pairing: ExtensionPairing) -> ExtensionPairing:
        self.pairings[pairing.id] = pairing
        return pairing

    def get_by_user_code(self, user_code: PairingUserCode) -> ExtensionPairing | None:
        # A copy, as a real repository would return one. Handing out the stored
        # object would make the entity's in-memory checks and the store the same
        # thing, and no use-case test could ever show a write landing on a row
        # that changed since it was read.
        for pairing in self.pairings.values():
            if pairing.user_code == user_code:
                return replace(pairing)
        return None

    def approve(self, pairing_id: UUID, user_id: UUID, now: datetime) -> bool:
        # Mirrors the SQL conditional UPDATE: only a pairing that is still
        # pending in the STORE, whatever the caller's copy says, can change.
        pairing = self._still_pending(pairing_id, now)
        if pairing is None:
            return False
        pairing.approved_at = now
        pairing.approved_by_user_id = user_id
        return True

    def deny(self, pairing_id: UUID, now: datetime) -> bool:
        pairing = self._still_pending(pairing_id, now)
        if pairing is None:
            return False
        pairing.denied_at = now
        return True

    def consume(self, pairing_id: UUID, now: datetime) -> bool:
        # Mirrors the SQL conditional UPDATE: only an approved, un-denied,
        # un-consumed, unexpired pairing can be redeemed, and only once. A fake
        # that merely stamped the timestamp would let a use-case test pass
        # while the real single-mint guarantee was broken.
        pairing = self.pairings.get(pairing_id)
        if pairing is None:
            return False
        if (
            pairing.is_consumed()
            or pairing.denied_at is not None
            or pairing.approved_at is None
            or pairing.is_expired(now)
        ):
            return False
        pairing.mark_consumed(now)
        return True

    def _still_pending(self, pairing_id: UUID, now: datetime) -> ExtensionPairing | None:
        pairing = self.pairings.get(pairing_id)
        if pairing is None or pairing.is_resolved() or pairing.is_consumed() or pairing.is_expired(now):
            return None
        return pairing

    def purge_expired(self, cutoff: datetime) -> None:
        self.purge_cutoffs.append(cutoff)
        expired = [pairing_id for pairing_id, pairing in self.pairings.items() if pairing.expires_at < cutoff]
        for pairing_id in expired:
            del self.pairings[pairing_id]
