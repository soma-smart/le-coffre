from dataclasses import replace
from datetime import datetime
from uuid import UUID

from vault_management_context.application.gateways import ShareLinkRepository
from vault_management_context.domain.entities import ShareLink
from vault_management_context.domain.value_objects import ShareLinkDelivery


class FakeShareLinkRepository(ShareLinkRepository):
    def __init__(self):
        self._links: dict[UUID, ShareLink] = {}
        self._lose_next_first_delivery_race = False
        self._lose_next_removal_race = False

    def lose_next_first_delivery_race(self, delivered_at: datetime, reopenable_until: datetime) -> None:
        """Make the next first delivery behave as if another request got there first."""
        self._lose_next_first_delivery_race = True
        self._race_winner = (delivered_at, reopenable_until)

    def lose_next_removal_race(self) -> None:
        """Make the next removal behave as if another request removed it first."""
        self._lose_next_removal_race = True

    def stored(self) -> list[ShareLink]:
        """Test helper: what is currently stored, ordered by share index."""
        return sorted((replace(link) for link in self._links.values()), key=lambda link: link.share_index)

    def replace_all(self, links: list[ShareLink]) -> None:
        self._links = {link.id: replace(link) for link in links}

    def get_by_lookup_hash(self, lookup_hash: str) -> ShareLink | None:
        for link in self._links.values():
            if link.lookup_hash == lookup_hash:
                return replace(link)
        return None

    def deliver(self, link_id: UUID, now: datetime, reopenable_until: datetime) -> ShareLinkDelivery | None:
        link = self._links.get(link_id)
        if link is None or not link.can_be_delivered(now):
            return None
        if self._lose_next_first_delivery_race and not link.is_delivered():
            self._lose_next_first_delivery_race = False
            link.delivered_at, link.reopenable_until = self._race_winner
        if not link.is_delivered():
            link.delivered_at, link.reopenable_until = now, reopenable_until
            return ShareLinkDelivery(first_delivered_at=now, reopenable_until=reopenable_until, reopened=False)
        if not link.can_be_delivered(now):
            return None
        return ShareLinkDelivery(
            first_delivered_at=link.delivered_at,  # type: ignore[arg-type]
            reopenable_until=link.reopenable_until,  # type: ignore[arg-type]
            reopened=True,
        )

    def remove_delivered(self, link_id: UUID, now: datetime) -> bool:
        if self._lose_next_removal_race:
            self._lose_next_removal_race = False
            return False
        link = self._links.get(link_id)
        if link is None or not link.can_be_acknowledged(now):
            return False
        del self._links[link_id]
        return True

    def purge_expired(self, now: datetime) -> None:
        self._links = {link_id: link for link_id, link in self._links.items() if not link.is_purgeable(now)}
