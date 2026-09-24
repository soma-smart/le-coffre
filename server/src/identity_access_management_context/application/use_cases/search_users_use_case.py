from identity_access_management_context.application.commands import SearchUsersCommand
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User
from shared_kernel.application.tracing import TracedUseCase


class SearchUsersUseCase(TracedUseCase):
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, command: SearchUsersCommand) -> list[User]:
        return self.user_repository.search(command.query)
