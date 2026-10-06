from dataclasses import replace
from datetime import datetime
from uuid import UUID

from vault_management_context.application.gateways import ShareLinkRepository
from vault_management_context.domain.entities import ShareLink


class FakeShareLinkRepository(ShareLinkRepository):
    def __init__(self):
        self._links: dict[UUID, ShareLink] = {}
        self._lose_next_retrieval_race = False

    def lose_next_retrieval_race(self) -> None:
        """Make the next consume behave as if another request won it."""
        self._lose_next_retrieval_race = True

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

    def consume(self, link_id: UUID, now: datetime) -> bool:
        if self._lose_next_retrieval_race:
            self._lose_next_retrieval_race = False
            return False
        link = self._links.get(link_id)
        if link is None or now >= link.expires_at:
            return False
        del self._links[link_id]
        return True

    def purge_expired(self, now: datetime) -> None:
        self._links = {link_id: link for link_id, link in self._links.items() if now < link.expires_at}
