from identity_access_management_context.application.commands import (
    DemoteOwnerToMemberCommand,
)
from identity_access_management_context.application.gateways import (
    GroupEventRepository,
    GroupMemberRepository,
    GroupRepository,
    UserRepository,
)
from identity_access_management_context.domain.events import OwnerDemotedToMemberEvent
from identity_access_management_context.domain.exceptions import (
    CannotDemoteLastOwnerException,
    CannotDemoteOtherOwnerException,
    CannotModifyPersonalGroupException,
    GroupNotFoundException,
    UserNotFoundException,
    UserNotMemberOfGroupException,
    UserNotOwnerOfGroupException,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class DemoteOwnerToMemberUseCase(TracedUseCase):
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
        group_member_repository: GroupMemberRepository,
        event_publisher: DomainEventPublisher,
        group_event_repository: GroupEventRepository,
    ):
        self.user_repository = user_repository
        self.group_repository = group_repository
        self.group_member_repository = group_member_repository
        self._event_publisher = event_publisher
        self._group_event_repository = group_event_repository

    def execute(self, command: DemoteOwnerToMemberCommand) -> None:
        group = self.group_repository.get_by_id(command.group_id)
        if group is None:
            raise GroupNotFoundException(command.group_id)

        if group.is_personal:
            raise CannotModifyPersonalGroupException(command.group_id)

        requester_id = command.requesting_user.user_id
        is_admin = AdminPermissionChecker.is_admin(command.requesting_user)
        is_owner = self.group_member_repository.is_owner(command.group_id, requester_id)
        if not (is_admin or is_owner):
            raise UserNotOwnerOfGroupException(requester_id, command.group_id)

        # A regular owner may only step themselves down. Demoting someone
        # else is an admin-only power — matching the UI, which only ever
        # shows the demote button on another owner's card to an admin.
        if not is_admin and requester_id != command.user_id:
            raise CannotDemoteOtherOwnerException(requester_id, command.user_id, command.group_id)

        user = self.user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        if not self.group_member_repository.is_member(command.group_id, command.user_id):
            raise UserNotMemberOfGroupException(command.user_id, command.group_id)

        if not self.group_member_repository.is_owner(command.group_id, command.user_id):
            # Already a plain member — idempotent no-op, mirroring
            # AddOwnerToGroupUseCase's "already an owner" idempotency.
            # Nothing actually changes, so nothing should be published or
            # logged: doing so would record a false "owner demoted" audit
            # entry for someone who was never an owner.
            return

        # count_owners_for_update() rather than count_owners(): this is a
        # check-then-act on the same data the write below depends on. A
        # plain read here would let two concurrent demotes of a two-owner
        # group both see count == 2, both pass this check, and both commit —
        # leaving the group with no owners. The locking read serializes
        # concurrent callers on the same group so the second one re-checks
        # against the first one's committed result.
        if self.group_member_repository.count_owners_for_update(command.group_id) <= 1:
            raise CannotDemoteLastOwnerException(command.user_id, command.group_id)

        self.group_member_repository.add_member(command.group_id, command.user_id, is_owner=False)

        event = OwnerDemotedToMemberEvent(
            group_id=command.group_id,
            user_id=command.user_id,
            demoted_by_user_id=requester_id,
        )
        self._event_publisher.publish(event)
        self._group_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=requester_id,
            event_data={"group_id": str(command.group_id), "user_id": str(command.user_id)},
        )
