from identity_access_management_context.application.responses.can_create_admin_response import (
    CanCreateAdminResponse,
)
from identity_access_management_context.application.gateways import UserRepository
from identity_access_management_context.application.services import AdminExistenceService


class CanCreateAdminUseCase:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self) -> CanCreateAdminResponse:
        admin_exists = AdminExistenceService.admin_exists(self.user_repository)
        return CanCreateAdminResponse(can_create=not admin_exists)
