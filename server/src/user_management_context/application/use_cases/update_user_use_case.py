from user_management_context.application.interfaces import UserRepository
from user_management_context.application.commands import UpdateUserCommand
from user_management_context.domain.exceptions import UserNotFoundError
from uuid import UUID


class UpdateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
    ):
        self.user_repository = user_repository

    def execute(self, command: UpdateUserCommand) -> UUID:
        user = self.user_repository.get_by_id(command.id)
        if not user:
            raise UserNotFoundError(command.id)

        user.username = command.username
        user.email = command.email
        user.name = command.name

        self.user_repository.update(user)
        return user.id
