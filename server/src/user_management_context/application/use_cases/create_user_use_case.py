from uuid import UUID

from user_management_context.application.commands import CreateUserCommand
from user_management_context.application.interfaces import UserRepository
from user_management_context.domain.entities import User


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
