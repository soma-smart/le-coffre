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

    def count_all(self) -> int:
        return len(self.storage)

    def count_active_all(self, now: datetime) -> int:
        return len(
            [
                link
                for link in self.storage.values()
                if not link.is_consumed() and not link.is_revoked() and not link.is_expired(now)
            ]
        )

    def _redeemable(self, link: OneTimeLink, now: datetime) -> bool:
        return not link.is_consumed() and not link.is_revoked() and not link.is_expired(now)

    def _matching(self, now: datetime, include_inactive: bool) -> list[OneTimeLink]:
        links = [link for link in self.storage.values() if include_inactive or self._redeemable(link, now)]
        return sorted(links, key=lambda link: link.created_at, reverse=True)

    def list_all(self, now: datetime, include_inactive: bool, limit: int) -> list[OneTimeLink]:
        return self._matching(now, include_inactive)[:limit]

    def count_all_matching(self, now: datetime, include_inactive: bool) -> int:
        return len(self._matching(now, include_inactive))

    def list_for_creator(
        self, created_by_user_id: UUID, now: datetime, include_inactive: bool, limit: int
    ) -> list[OneTimeLink]:
        mine = [link for link in self._matching(now, include_inactive) if link.created_by_user_id == created_by_user_id]
        return mine[:limit]

    def count_for_creator(self, created_by_user_id: UUID, now: datetime, include_inactive: bool) -> int:
        return len(
            [link for link in self._matching(now, include_inactive) if link.created_by_user_id == created_by_user_id]
        )

    def revoke_all_for_creator(self, created_by_user_id: UUID, now: datetime) -> int:
        revoked = 0
        for link in self.storage.values():
            if link.created_by_user_id != created_by_user_id:
                continue
            # Mirrors the SQL guard: an already-read link keeps its read timestamp.
            if link.is_consumed() or link.is_revoked():
                continue
            link.mark_revoked(now)
            revoked += 1
        return revoked

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
