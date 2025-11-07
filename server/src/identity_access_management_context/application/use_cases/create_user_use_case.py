from uuid import UUID

from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User


class CreateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
    ):
        self.user_repository = user_repository

    def execute(self, command: CreateUserCommand) -> UUID:
        user = User(
            id=command.id,
            username=command.username,
            email=command.email,
            name=command.name,
        )

        self.user_repository.save(user)

        return user.id
