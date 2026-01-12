from uuid import UUID

from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
)
from password_management_context.application.responses import (
    ListAccessResponse,
    AccessResponse,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    PasswordAccessDeniedError,
)
from password_management_context.domain.value_objects import PasswordPermission


class ListAccessUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository

    def execute(self, requester_id: UUID, password_id: UUID) -> ListAccessResponse:
        password_data = self.password_repository.get_by_id(password_id)
        if not password_data:
            raise PasswordNotFoundError(password_id)

        if not self.password_permissions_repository.has_access(
            requester_id, password_id, PasswordPermission.READ
        ):
            raise PasswordAccessDeniedError(requester_id, password_id)

        permissions = self.password_permissions_repository.list_all_permissions_for(
            password_id
        )

        return ListAccessResponse(
            accesses=[
                AccessResponse(
                    user_id=user_id, permissions=permissions.get(user_id, set())
                )
                for user_id in permissions.keys()
            ]
        )
