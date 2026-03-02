from identity_access_management_context.application.gateways import UserRepository, UserEventRepository
from identity_access_management_context.application.commands import UpdateUserCommand
from identity_access_management_context.domain.events import UserUpdatedEvent
from identity_access_management_context.domain.exceptions import UserNotFoundError
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.domain.services import AdminPermissionChecker
from shared_kernel.adapters.primary.exceptions import NotAdminError
from uuid import UUID


class UpdateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        event_publisher: DomainEventPublisher,
        user_event_repository: UserEventRepository,
    ):
        self.user_repository = user_repository
        self._event_publisher = event_publisher
        self._user_event_repository = user_event_repository

    def execute(self, command: UpdateUserCommand) -> UUID:
        if command.requesting_user.user_id != command.id and not AdminPermissionChecker.is_admin(command.requesting_user):
            raise NotAdminError("Only administrators can update other users")

        user = self.user_repository.get_by_id(command.id)
        if not user:
            raise UserNotFoundError(command.id)

        user.username = command.username
        user.email = command.email
        user.name = command.name

        self.user_repository.update(user)

        event = UserUpdatedEvent(
            user_id=command.id,
            updated_by_user_id=command.requesting_user.user_id,
        )
        self._event_publisher.publish(event)
        self._user_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.requesting_user.user_id,
            event_data={"user_id": str(command.id)},
        )

        return user.id
