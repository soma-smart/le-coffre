from user_management_context.application.gateways import UserRepository
from uuid import UUID
from user_management_context.domain.entities import User


class GetUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, user_id: UUID) -> User:
        return self.user_repository.get_by_id(user_id)

    def execute_by_email(self, email: str) -> User:
        return self.user_repository.get_by_email(email)
