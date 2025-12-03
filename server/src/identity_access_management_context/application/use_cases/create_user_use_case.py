from uuid import UUID

from identity_access_management_context.application.commands import CreateUserCommand
from identity_access_management_context.application.gateways import (
    UserRepository,
    PasswordHashingGateway,
)
from identity_access_management_context.domain.entities import User


class CreateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        password_hashing_gateway: PasswordHashingGateway,
    ):
        self.user_repository = user_repository
        self.password_hashing_gateway = password_hashing_gateway

    def execute(self, command: CreateUserCommand) -> UUID:
        password_hash = None
        if command.password:
            password_hash = self.password_hashing_gateway.hash(command.password)

        user = User(
            id=command.id,
            username=command.username,
            email=command.email,
            name=command.name,
            password_hash=password_hash,
        )

        self.user_repository.save(user)

        return user.id
