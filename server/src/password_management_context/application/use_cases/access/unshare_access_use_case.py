from password_management_context.application.commands import UnshareResourceCommand
from password_management_context.application.gateways import (
    PasswordRepository,
    PasswordPermissionsRepository,
    GroupAccessGateway,
)
from password_management_context.domain.exceptions import (
    PasswordAccessDeniedError,
    CannotUnshareWithOwnerError,
    PasswordNotFoundError,
    UserNotOwnerOfGroupError,
    GroupNotFoundError,
)


class UnshareAccessUseCase:
    def __init__(
        self,
        password_repository: PasswordRepository,
        password_permissions_repository: PasswordPermissionsRepository,
        group_access_gateway: GroupAccessGateway,
    ):
        self.password_repository = password_repository
        self.password_permissions_repository = password_permissions_repository
        self.group_access_gateway = group_access_gateway

    def execute(self, command: UnshareResourceCommand):
        # Verify the password exists
        if not self.password_repository.get_by_id(command.password_id):
            raise PasswordNotFoundError(command.password_id)

        # Verify the target group exists
        if not self.group_access_gateway.group_exists(command.group_id):
            raise GroupNotFoundError(command.group_id)

        # Get the owner group of the password
        all_permissions = self.password_permissions_repository.list_all_permissions_for(
            command.password_id
        )

        # Find the owner group
        owner_group_id = None
        for entity_id, (is_owner, _) in all_permissions.items():
            if is_owner:
                owner_group_id = entity_id
                break

        if not owner_group_id:
            raise PasswordAccessDeniedError(command.owner_id, command.password_id)

        # Check if the requester owns the group that owns the password
        if not self.group_access_gateway.is_user_owner_of_group(
            command.owner_id, owner_group_id
        ):
            raise UserNotOwnerOfGroupError(command.owner_id, owner_group_id)

        # Cannot unshare with the owner group
        if command.group_id == owner_group_id:
            raise CannotUnshareWithOwnerError(command.group_id, command.password_id)

        # Revoke all access from the target group
        self.password_permissions_repository.revoke_access(
            command.group_id, command.password_id
        )
