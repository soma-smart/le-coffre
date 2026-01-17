from typing import Optional
from uuid import UUID
from sqlmodel import Session, select

from identity_access_management_context.application.gateways import GroupRepository
from identity_access_management_context.domain.entities import PersonalGroup, Group
from .model.personal_group_model import PersonalGroupTable
from .model.group_model import GroupTable


class SqlGroupRepository(GroupRepository):
    def __init__(self, session: Session):
        self._session = session

    def save_personal_group(self, group: PersonalGroup) -> None:
        """Save a personal group to the repository."""
        personal_group_table = PersonalGroupTable(
            id=group.id,
            name=group.name,
            user_id=group.user_id,
        )
        self._session.add(personal_group_table)
        self._session.commit()

    def get_all(self) -> list[PersonalGroup]:
        """Get all personal groups."""
        statement = select(PersonalGroupTable)
        results = self._session.exec(statement).all()
        return [
            PersonalGroup(
                id=result.id,
                name=result.name,
                user_id=result.user_id,
            )
            for result in results
        ]

    def get_by_user_id(self, user_id: UUID) -> Optional[PersonalGroup]:
        """Get a personal group by user ID."""
        statement = select(PersonalGroupTable).where(
            PersonalGroupTable.user_id == user_id
        )
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return PersonalGroup(
            id=result.id,
            name=result.name,
            user_id=result.user_id,
        )

    def save_group(self, group: Group) -> None:
        """Save a group to the repository."""
        group_table = GroupTable(
            id=group.id,
            name=group.name,
            is_personal=group.is_personal,
        )
        self._session.add(group_table)
        self._session.commit()

    def get_by_id(self, group_id: UUID) -> Optional[Group]:
        """Get a group by ID."""
        statement = select(GroupTable).where(GroupTable.id == group_id)
        result = self._session.exec(statement).first()
        if result is None:
            return None
        return Group(
            id=result.id,
            name=result.name,
            is_personal=result.is_personal,
        )
