from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.commands import GetUserMeCommand
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import UserNotFoundException


class GetUserMeUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: GetUserMeCommand) -> User:
        if command.user_id != command.requesting_user_id:
            raise UserNotFoundException(command.user_id)

        user = self.user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFoundException(command.user_id)

        return user
