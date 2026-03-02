from identity_access_management_context.application.commands import (
    UpdateUserPasswordCommand,
)
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
    UserEventRepository,
)
from identity_access_management_context.domain.events import UserPasswordChangedEvent
from identity_access_management_context.domain.exceptions import (
    UserNotFoundException,
    InvalidCredentialsException,
)
from shared_kernel.application.gateways import DomainEventPublisher


class UpdateUserPasswordUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        password_hashing_gateway: PasswordHashingGateway,
        event_publisher: DomainEventPublisher,
        user_event_repository: UserEventRepository,
    ):
        self.user_password_repository = user_password_repository
        self.password_hashing_gateway = password_hashing_gateway
        self._event_publisher = event_publisher
        self._user_event_repository = user_event_repository

    def execute(self, command: UpdateUserPasswordCommand) -> None:
        user_password = self.user_password_repository.get_by_id(command.user_id)
        if not user_password:
            raise UserNotFoundException(command.user_id)

        if not self.password_hashing_gateway.verify(
            command.old_password, user_password.password_hash
        ):
            raise InvalidCredentialsException("Invalid old password")

        new_password_hash = self.password_hashing_gateway.hash(command.new_password)

        self.user_password_repository.update_password(
            command.user_id, new_password_hash
        )

        event = UserPasswordChangedEvent(user_id=command.user_id)
        self._event_publisher.publish(event)
        self._user_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=command.user_id,
            event_data={"user_id": str(command.user_id)},
        )
