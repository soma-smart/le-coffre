from uuid import UUID

from notification_context.domain.value_objects import OneTimeLinkDetails


class FakeOneTimeLinkGateway:
    def __init__(self):
        self._links: dict[UUID, OneTimeLinkDetails] = {}
        self._failing: set[UUID] = set()

    def add(self, link: OneTimeLinkDetails) -> None:
        self._links[link.link_id] = link

    def fail_for(self, link_id: UUID) -> None:
        self._failing.add(link_id)

    def get_link(self, link_id: UUID) -> OneTimeLinkDetails | None:
        if link_id in self._failing:
            raise RuntimeError("password context unavailable")
        return self._links.get(link_id)
