from identity_access_management_context.application.commands import PromoteAdminCommand
from identity_access_management_context.application.gateways import UserRepository, UserEventRepository
from identity_access_management_context.domain.events import AdminPromotedEvent
from identity_access_management_context.domain.exceptions import UserNotFoundException
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.domain.services import AdminPermissionChecker


class PromoteAdminUseCase:
    def __init__(self, user_repository: UserRepository, event_publisher: DomainEventPublisher, user_event_repository: UserEventRepository):
        self.user_repository = user_repository
        self._event_publisher = event_publisher
        self._user_event_repository = user_event_repository

    def execute(self, command: PromoteAdminCommand) -> None:
        AdminPermissionChecker.ensure_admin(
            command.requesting_user, "promote users to admin"
        )

        user = self.user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        user.promote_to_admin()
        self.user_repository.update(user)

        event = AdminPromotedEvent(
            user_id=command.user_id,
            promoted_by_user_id=command.requesting_user.user_id,
        )
        self._event_publisher.publish(event)
        self._user_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.requesting_user.user_id,
            event_data={"user_id": str(command.user_id)},
        )
