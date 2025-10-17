from typing import Protocol

from group_management_context.domain.group import Group


class GroupRepository(Protocol):
    def save(self, group: Group) -> None: ...

    def exists_by_name(self, name: str) -> bool: ...
