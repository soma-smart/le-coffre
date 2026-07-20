from datetime import datetime
from uuid import UUID

from password_management_context.application.gateways import OneTimeLinkRepository
from password_management_context.domain.entities import OneTimeLink


class FakeOneTimeLinkRepository(OneTimeLinkRepository):
    def __init__(self):
        self.storage: dict[UUID, OneTimeLink] = {}

    def add(self, link: OneTimeLink) -> None:
        self.storage[link.id] = link

    def get_by_id(self, link_id: UUID) -> OneTimeLink | None:
        return self.storage.get(link_id)

    def get_by_token_hash(self, token_hash: str) -> OneTimeLink | None:
        for link in self.storage.values():
            if link.token_hash == token_hash:
                return link
        return None

    def list_for_password(self, password_id: UUID, limit: int) -> list[OneTimeLink]:
        links = [link for link in self.storage.values() if link.password_id == password_id]
        return sorted(links, key=lambda link: link.created_at, reverse=True)[:limit]

    def list_active_for_password(self, password_id: UUID, now: datetime, limit: int) -> list[OneTimeLink]:
        links = [
            link
            for link in self.storage.values()
            if link.password_id == password_id
            and not link.is_consumed()
            and not link.is_revoked()
            and not link.is_expired(now)
        ]
        return sorted(links, key=lambda link: link.created_at, reverse=True)[:limit]

    def count_for_password(self, password_id: UUID) -> int:
        return len([link for link in self.storage.values() if link.password_id == password_id])

    def count_active_for_password(self, password_id: UUID, now: datetime) -> int:
        return len(
            [
                link
                for link in self.storage.values()
                if link.password_id == password_id
                and not link.is_consumed()
                and not link.is_revoked()
                and not link.is_expired(now)
            ]
        )

    def consume(self, link_id: UUID, now: datetime) -> bool:
        # Mirrors the SQL adapter's conditional UPDATE: only the first caller on
        # an unread, unrevoked link gets True.
        link = self.storage.get(link_id)
        if link is None or link.is_consumed() or link.is_revoked():
            return False
        link.mark_read(now)
        return True

    def revoke(self, link_id: UUID, now: datetime) -> bool:
        link = self.storage.get(link_id)
        if link is None or link.is_consumed() or link.is_revoked():
            return False
        link.mark_revoked(now)
        return True

    def delete_for_password(self, password_id: UUID) -> None:
        for link_id in [lid for lid, link in self.storage.items() if link.password_id == password_id]:
            del self.storage[link_id]
