from uuid import UUID
from user_management_context.application.gateways import UserRepository


class DeleteUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, user_id: UUID) -> None:
        self.user_repository.delete(user_id)
