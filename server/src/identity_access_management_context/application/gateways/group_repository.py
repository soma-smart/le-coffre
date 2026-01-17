from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import PersonalGroup, Group


class GroupRepository(Protocol):
    def save_personal_group(self, group: PersonalGroup) -> None:
        """Save a personal group to the repository."""
        ...

    def get_all(self) -> list[Group]:
        """Get all groups."""
        ...

    def save_group(self, group: Group) -> None:
        """Save a group to the repository."""
        ...

    def get_by_id(self, group_id: UUID) -> Group | None:
        """Get a group by ID."""
        ...
