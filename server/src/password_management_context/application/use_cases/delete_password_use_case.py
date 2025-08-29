from uuid import UUID
from password_management_context.application.gateways import PasswordRepository


class DeletePasswordUseCase:
    def __init__(self, password_repository: PasswordRepository):
        self.password_repository = password_repository

    def execute(self, password_id: UUID) -> None:
        self.password_repository.delete(password_id)
