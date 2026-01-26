from identity_access_management_context.application.commands import GetUserCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.exceptions import UserNotFoundError


class GetUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: GetUserCommand) -> User:
        if command.user_id is not None:
            ret = self.user_repository.get_by_id(command.user_id)
            if ret:
                return ret
            raise UserNotFoundError(command.user_id)

        if command.user_email is not None:
            ret = self.user_repository.get_by_email(command.user_email)
            if ret:
                return ret
            raise UserNotFoundError(command.user_email)

        raise ValueError("Either user_id or user_email must be provided.")
