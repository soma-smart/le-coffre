from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.domain.entities import User


class ListUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self) -> list[User]:
        return self.user_repository.list_all()
