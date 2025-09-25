from uuid import UUID

from password_management_context.application.commands import CreatePasswordCommand
from password_management_context.application.gateways import PasswordRepository
from password_management_context.domain.entities import Password
from password_management_context.domain.services.password_complexity_service import (
    PasswordComplexityService,
)
from password_management_context.domain.events import PasswordCreatedEvent
from shared_kernel.encryption import EncryptionService
from shared_kernel.pubsub import DomainEventPublisher


class CreatePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        encryption_service: EncryptionService,
        domain_event_publisher: DomainEventPublisher,
    ):
        self.password_repository = password_repository
        self.encryption_service = encryption_service
        self.domain_event_publisher = domain_event_publisher

    def execute(self, command: CreatePasswordCommand) -> UUID:
        PasswordComplexityService.validate(command.decrypted_password)

        encrypted_value = self.encryption_service.encrypt(command.decrypted_password)

        password = Password(
            id=command.id,
            name=command.name,
            encrypted_value=encrypted_value,
            folder=command.folder,
        )

        self.password_repository.save(password)

        self.domain_event_publisher.publish(
            PasswordCreatedEvent.create(
                password_id=command.id,
                created_by=command.user_id,
                name=command.name,
                folder=command.folder,
            )
        )

        return password.id
