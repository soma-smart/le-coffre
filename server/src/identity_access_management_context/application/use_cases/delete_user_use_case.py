from identity_access_management_context.application.gateways import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
)
from identity_access_management_context.application.commands import DeleteUserCommand
from identity_access_management_context.domain.events import UserDeletedEvent
from shared_kernel.domain.services import AdminPermissionChecker
from shared_kernel.application.gateways import DomainEventPublisher


class DeleteUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        event_publisher: DomainEventPublisher,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self.event_publisher = event_publisher

    def execute(self, command: DeleteUserCommand) -> None:
        AdminPermissionChecker().ensure_admin(command.requesting_user, "delete users")
        user_id = command.user_id

        personal_group = self.group_repository.get_by_user_id(user_id)
        personal_group_id = personal_group.id if personal_group else None

        # Delete groups where user is the sole owner (excluding personal group)
        all_groups = self.group_repository.get_all()
        for group in all_groups:
            if group.is_personal:
                continue

            if self.group_member_repository.is_owner(group.id, user_id):
                owner_count = self.group_member_repository.count_owners(group.id)
                if owner_count == 1:
                    self.group_member_repository.delete_by_group_id(group.id)
                    self.group_repository.delete_group(group.id)

        # Remove user from all remaining groups (including as owner/member) in one operation
        self.group_member_repository.remove_user_from_all_groups(user_id)

        self.user_repository.delete(user_id)

        event = UserDeletedEvent(
            user_id=user_id,
            deleted_by_user_id=command.requesting_user.user_id,
            personal_group_id=personal_group_id,
        )
        self.event_publisher.publish(event)

        # Delete personal group after event (so password context can clean up)
        if personal_group:
            self.group_repository.delete_group(personal_group.id)
