from uuid import UUID

from user_management_context.application.commands import CreateUserCommand
from user_management_context.application.interfaces import UserRepository
from user_management_context.domain.entities import User
from user_management_context.application.interfaces import HashingGateway
from shared_kernel.access_control import AccessController, Granted, AccessDeniedError


class CreateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        hash_password_service: HashingGateway,
        assess_controller: AccessController,
    ):
        self.user_repository = user_repository
        self.hash_password_service = hash_password_service
        self.access_controller = assess_controller

    def execute(self, requester_id: UUID, command: CreateUserCommand) -> UUID:
        check_permission = self.access_controller.check_create_access(
            requester_id, self.user_repository.resource_id
        )
        if check_permission.granted != Granted.ACCESS:
            raise AccessDeniedError(requester_id, self.user_repository.resource_id)

        password_hashed = self.hash_password_service.hash(command.password)

        user = User(
            id=command.id,
            username=command.username,
            email=command.email,
            password_hashed=password_hashed,
        )

        self.user_repository.save(user)
        # Read access to users resource
        self.access_controller.grant_access(
            command.id, self.user_repository.resource_id
        )
        # Owner access to own user resource
        self.access_controller.grant_access(command.id, command.id)
        self.access_controller.grant_update_access(command.id, command.id)
        self.access_controller.grant_delete_access(command.id, command.id)

        return user.id
