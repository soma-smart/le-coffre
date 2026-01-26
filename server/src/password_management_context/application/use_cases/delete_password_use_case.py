from password_management_context.application.commands import DeletePasswordCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.domain.exceptions import (
    PasswordNotFoundError,
    NotPasswordOwnerError,
    UserNotOwnerOfGroupError,
)


class DeletePasswordUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway

    def execute(self, command: DeletePasswordCommand) -> None:
        if not self.password_repository.get_by_id(command.password_id):
            raise PasswordNotFoundError(command.password_id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            command.password_id
        )

        # Find the owner group (there should be exactly one)
        owner_group_id = None
        for entity_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise NotPasswordOwnerError(command.requester_id, command.password_id)

        # Check if the user owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(
            command.requester_id, owner_group_id
        ):
            raise UserNotOwnerOfGroupError(command.requester_id, owner_group_id)

        self.password_repository.delete(command.password_id)
