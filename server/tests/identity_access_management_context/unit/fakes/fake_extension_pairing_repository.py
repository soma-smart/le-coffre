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
        for pairing in self.pairings.values():
            if pairing.user_code == user_code:
                return pairing
        return None

    def save(self, pairing: ExtensionPairing) -> None:
        if pairing.id in self.pairings:
            self.pairings[pairing.id] = pairing

    def consume(self, pairing_id: UUID, now: datetime) -> bool:
        # Mirrors the SQL conditional UPDATE: only an approved, un-denied,
        # un-consumed pairing can be redeemed, and only once. A fake that
        # merely stamped the timestamp would let a use-case test pass while the
        # real single-mint guarantee was broken.
        pairing = self.pairings.get(pairing_id)
        if pairing is None:
            return False
        if pairing.is_consumed() or pairing.denied_at is not None or pairing.approved_at is None:
            return False
        pairing.mark_consumed(now)
        return True

    def purge_expired(self, cutoff: datetime) -> None:
        self.purge_cutoffs.append(cutoff)
        expired = [pairing_id for pairing_id, pairing in self.pairings.items() if pairing.expires_at < cutoff]
        for pairing_id in expired:
            del self.pairings[pairing_id]
