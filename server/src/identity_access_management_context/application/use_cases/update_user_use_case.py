from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.commands import UpdateUserCommand
from identity_access_management_context.domain.events import UserUpdatedEvent
from identity_access_management_context.domain.exceptions import UserNotFoundError
from shared_kernel.application.gateways import DomainEventPublisher
from uuid import UUID


class UpdateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        event_publisher: DomainEventPublisher,
    ):
        self.user_repository = user_repository
        self._event_publisher = event_publisher

    def execute(self, command: UpdateUserCommand) -> UUID:
        user = self.user_repository.get_by_id(command.id)
        if not user:
            raise UserNotFoundError(command.id)

        user.username = command.username
        user.email = command.email
        user.name = command.name

        self.user_repository.update(user)

        self._event_publisher.publish(UserUpdatedEvent(
            user_id=command.id,
            updated_by_user_id=command.id,
        ))

        return user.id
