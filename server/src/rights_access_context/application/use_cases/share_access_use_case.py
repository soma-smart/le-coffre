from rights_access_context.application.commands import ShareResourceCommand
from rights_access_context.application.gateways import UserManagementGateway, RightsRepository
from rights_access_context.domain.exceptions import (
    PermissionDeniedError,
    UserNotFoundError,
)
from rights_access_context.domain.value_objects import Permission


class ShareAccessUseCase:
    def __init__(self, rights_repository: RightsRepository, user_management_gateway: UserManagementGateway):
        self.rights_repository = rights_repository
        self.user_management_gateway = user_management_gateway

    def execute(self, command: ShareResourceCommand):
        if not self.user_management_gateway.user_exists(command.user_id):
            raise UserNotFoundError(command.user_id)

        if not self.rights_repository.is_owner(
            command.owner_id, command.resource_id
        ):
            raise PermissionDeniedError(command.owner_id, command.resource_id)

        self.rights_repository.add_permission(command.user_id, command.resource_id, Permission.READ)
