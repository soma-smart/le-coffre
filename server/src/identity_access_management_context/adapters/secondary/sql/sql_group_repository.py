from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from identity_access_management_context.application.gateways import GroupRepository
from identity_access_management_context.domain.entities import Group, PersonalGroup
from shared_kernel.adapters.secondary.sql import SQLBaseRepository

from .model.group_model import GroupTable


class SqlGroupRepository(SQLBaseRepository, GroupRepository):
    def __init__(self, session: Session):
        super().__init__(session)

    def save_personal_group(self, group: PersonalGroup) -> None:
        """Save a personal group to the repository."""
        group_table = GroupTable(
            id=group.id,
            name=group.name,
            is_personal=True,
            user_id=group.user_id,
        )
        self._session.add(group_table)
        self.commit()

    def count_non_personal(self) -> int:
        """Count non-personal groups."""
        statement = select(func.count()).select_from(GroupTable).where(col(GroupTable.is_personal).is_(False))
        return self._session.exec(statement).one()

    def get_all(self) -> list[Group]:
        """Get all groups."""
        statement = select(GroupTable)
        results = self._session.exec(statement).all()
        return [
            Group(
                id=result.id,
                name=result.name,
                is_personal=result.is_personal,
                user_id=result.user_id,
            )
            for result in results
        ]

    def get_by_user_id(self, user_id: UUID) -> PersonalGroup | None:
        """Get a personal group by user ID."""
        statement = select(GroupTable).where(GroupTable.user_id == user_id, GroupTable.is_personal)
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return PersonalGroup(
            id=result.id,
            name=result.name,
            user_id=result.user_id,  # type: ignore
        )

    def save_group(self, group: Group) -> None:
        """Save a group to the repository."""
        group_table = GroupTable(
            id=group.id,
            name=group.name,
            is_personal=group.is_personal,
            user_id=group.user_id,
        )
        self._session.merge(group_table)
        self.commit()

    def get_by_id(self, group_id: UUID) -> Group | None:
        """Get a group by ID."""
        statement = select(GroupTable).where(GroupTable.id == group_id)
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return Group(
            id=result.id,
            name=result.name,
            is_personal=result.is_personal,
            user_id=result.user_id,
        )

    def delete_group(self, group_id: UUID) -> None:
        """Delete a group from the repository."""
        statement = select(GroupTable).where(GroupTable.id == group_id)
        result = self._session.exec(statement).first()
        if result is not None:
            self._session.delete(result)
            self.commit()

    def get_by_name(self, group_name: str) -> Group | None:
        """Get a group by name."""
        statement = select(GroupTable).where(GroupTable.name == group_name)
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return Group(
            id=result.id,
            name=result.name,
            is_personal=result.is_personal,
            user_id=result.user_id,
        )
