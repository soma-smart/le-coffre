from identity_access_management_context.application.commands import PromoteAdminCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.events import AdminPromotedEvent
from identity_access_management_context.domain.exceptions import UserNotFoundException
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.domain.services import AdminPermissionChecker


class PromoteAdminUseCase:
    def __init__(self, user_repository: UserRepository, event_publisher: DomainEventPublisher):
        self.user_repository = user_repository
        self._event_publisher = event_publisher

    def execute(self, command: PromoteAdminCommand) -> None:
        AdminPermissionChecker.ensure_admin(
            command.requesting_user, "promote users to admin"
        )

        user = self.user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        user.promote_to_admin()
        self.user_repository.update(user)

        self._event_publisher.publish(AdminPromotedEvent(
            user_id=command.user_id,
            promoted_by_user_id=command.requesting_user.user_id,
        ))
