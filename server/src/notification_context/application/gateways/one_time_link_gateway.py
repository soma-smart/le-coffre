from typing import Protocol
from uuid import UUID

from notification_context.domain.value_objects import OneTimeLinkDetails


class OneTimeLinkGateway(Protocol):
    def get_link(self, link_id: UUID) -> OneTimeLinkDetails | None:
        """The link as it stands now; None if it, or its password, no longer exists"""
        ...
