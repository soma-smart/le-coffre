from uuid import UUID, uuid4

from identity_access_management_context.application.gateways import (
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.domain.entities import PersonalGroup


class UserCreationService:
    @staticmethod
    def create_personal_group_and_set_ownership(
        user_id: UUID,
        username: str,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
    ) -> UUID:
        group_id = uuid4()
        personal_group = PersonalGroup(
            id=group_id,
            name=f"{username}'s Personal Group",
            user_id=user_id,
        )

        group_repository.save_personal_group(personal_group)

        group_member_repository.add_member(group_id, user_id, is_owner=True)

        return group_id
