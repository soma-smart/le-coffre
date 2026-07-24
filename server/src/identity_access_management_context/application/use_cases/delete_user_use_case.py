import logging

from identity_access_management_context.application.commands import DeleteUserCommand
from identity_access_management_context.application.gateways import (
    GroupMemberRepository,
    GroupRepository,
    OneTimeLinkRevocationGateway,
    UserEventRepository,
    UserRepository,
)
from identity_access_management_context.domain.events import UserDeletedEvent
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker

logger = logging.getLogger(__name__)


class DeleteUserUseCase(TracedUseCase):
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        event_publisher: DomainEventPublisher,
        user_event_repository: UserEventRepository,
        one_time_link_revocation_gateway: OneTimeLinkRevocationGateway,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self.event_publisher = event_publisher
        self._user_event_repository = user_event_repository
        self._one_time_link_revocation_gateway = one_time_link_revocation_gateway

    def execute(self, command: DeleteUserCommand) -> None:
        AdminPermissionChecker().ensure_admin(command.requesting_user, "delete users")
        user_id = command.user_id

        # Cut the user's one-time links first. They grant anonymous reads that
        # outlive the account: a link on a password owned by a shared group stays
        # redeemable once its issuer is gone, because the password itself remains.
        # Doing it before the deletion means a later failure leaves the links
        # already dead rather than live and unowned.
        revoked_links = self._one_time_link_revocation_gateway.revoke_all_for_user(user_id)
        if revoked_links:
            logger.info(
                "Revoked one-time links of a deleted user",
                extra={"user_id": str(user_id), "revoked_count": revoked_links},
            )

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
        self._user_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.requesting_user.user_id,
            event_data={
                "user_id": str(user_id),
                "personal_group_id": str(personal_group_id) if personal_group_id else None,
            },
        )

        # Delete personal group after event (so password context can clean up)
        if personal_group:
            self.group_repository.delete_group(personal_group.id)
