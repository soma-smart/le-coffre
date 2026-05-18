from typing import Protocol
from uuid import UUID

from identity_access_management_context.domain.entities import Group, PersonalGroup


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

    def get_by_user_id(self, user_id: UUID) -> PersonalGroup | None:
        """Get a personal group by user ID."""
        ...

    def delete_group(self, group_id: UUID) -> None:
        """Delete a group from the repository."""
        ...

    def get_by_name(self, group_name: str) -> Group | None:
        """Get a group by name."""
        ...

    def count_non_personal(self) -> int:
        """Count non-personal groups."""
        ...
