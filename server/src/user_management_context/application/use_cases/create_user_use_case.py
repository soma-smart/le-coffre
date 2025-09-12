from uuid import UUID

from user_management_context.application.commands import CreateUserCommand
from user_management_context.application.interfaces import UserRepository
from user_management_context.domain.entities import User
from user_management_context.application.interfaces import HashingGateway


class CreateUserUseCase:
    def __init__(
        self, user_repository: UserRepository, hash_password_service: HashingGateway
    ):
        self.user_repository = user_repository
        self.hash_password_service = hash_password_service

    def execute(self, command: CreateUserCommand) -> UUID:
        password_hashed = self.hash_password_service.hash(command.password)

        user = User(
            id=command.id,
            username=command.username,
            email=command.email,
            password_hashed=password_hashed,
        )

        self.user_repository.save(user)

        return user.id
