from uuid import UUID
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    NotPasswordOwnerError,
)


class DeletePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository

    def execute(self, requester_id: UUID, password_id: UUID) -> None:
        if not self.password_repository.get_by_id(password_id):
            raise PasswordNotFoundError(password_id)

        if not self.password_permissions_repository.is_owner(requester_id, password_id):
            raise NotPasswordOwnerError(requester_id, password_id)

        self.password_repository.delete(password_id)
