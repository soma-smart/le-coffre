from uuid import UUID
from sqlmodel import Session, select, delete

from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
)
from identity_access_management_context.domain.entities import GroupMember
from .model.group_member_model import GroupMemberTable


class SqlGroupMemberRepository(GroupMemberRepository):
    def __init__(self, session: Session):
        self._session = session

    def add_member(self, group_id: UUID, user_id: UUID, is_owner: bool) -> None:
        """Add a member to a group."""
        # Check if member already exists
        statement = select(GroupMemberTable).where(
            GroupMemberTable.group_id == group_id,
            GroupMemberTable.user_id == user_id,
        )
        existing = self._session.exec(statement).first()

        if existing:
            # Update existing member
            existing.is_owner = is_owner
            self._session.add(existing)  # Explicitly add to session
            self._session.flush()  # Flush before commit
        else:
            # Add new member
            member = GroupMemberTable(
                group_id=group_id,
                user_id=user_id,
                is_owner=is_owner,
            )
            self._session.add(member)

        self._session.commit()
        if existing:
            self._session.refresh(existing)  # Refresh to ensure changes are persisted

    def remove_member(self, group_id: UUID, user_id: UUID) -> None:
        """Remove a member from a group."""
        statement = delete(GroupMemberTable).where(
            GroupMemberTable.group_id == group_id,
            GroupMemberTable.user_id == user_id,
        )
        self._session.execute(statement)
        self._session.commit()

    def is_member(self, group_id: UUID, user_id: UUID) -> bool:
        """Check if a user is a member of a group."""
        statement = select(GroupMemberTable).where(
            GroupMemberTable.group_id == group_id,
            GroupMemberTable.user_id == user_id,
        )
        result = self._session.exec(statement).first()
        return result is not None

    def is_owner(self, group_id: UUID, user_id: UUID) -> bool:
        """Check if a user is an owner of a group."""
        statement = select(GroupMemberTable).where(
            GroupMemberTable.group_id == group_id,
            GroupMemberTable.user_id == user_id,
        )
        result = self._session.exec(statement).first()
        return result is not None and result.is_owner

    def get_members(self, group_id: UUID) -> list[GroupMember]:
        """Get all members of a group."""
        statement = select(GroupMemberTable).where(
            GroupMemberTable.group_id == group_id
        )
        results = self._session.exec(statement).all()
        return [
            GroupMember(
                group_id=result.group_id,
                user_id=result.user_id,
                is_owner=result.is_owner,
            )
            for result in results
        ]

    def count_owners(self, group_id: UUID) -> int:
        """Count the number of owners in a group."""
        statement = select(GroupMemberTable).where(
            GroupMemberTable.group_id == group_id,
            GroupMemberTable.is_owner.is_(True),
        )
        results = self._session.exec(statement).all()
        return len(results)

    def delete_by_group_id(self, group_id: UUID) -> None:
        statement = select(GroupMemberTable).where(
            GroupMemberTable.group_id == group_id
        )
        self._session.delete(statement)
        self._session.commit()
