from user_management_context.application.gateways import UserRepository
from user_management_context.application.gateways.haching_gateway import (
  HashingGateway
)
from user_management_context.application.commands import UpdateUserCommand
from uuid import UUID


class UpdateUserUseCase:
    def __init__(
      self,
      user_repository: UserRepository,
      hash_gateway: HashingGateway
    ):
        self.user_repository = user_repository
        self.hash_gateway = hash_gateway

    def execute(self, user_id: UUID, command: UpdateUserCommand) -> UUID:
        user = self.user_repository.get_by_id(user_id)

        user.username = command.username
        user.email = command.email
        user.password_hashed = self.hash_gateway.hash(command.password)

        self.user_repository.update(user)
        return user.id
