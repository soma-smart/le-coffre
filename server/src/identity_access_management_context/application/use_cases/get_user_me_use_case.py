from identity_access_management_context.application.gateways import (
    UserRepository,
    SsoUserRepository,
)
from identity_access_management_context.application.commands import GetUserMeCommand
from identity_access_management_context.application.responses import GetUserMeResponse
from identity_access_management_context.domain.exceptions import UserNotFoundException


class GetUserMeUseCase:
    def __init__(
        self, user_repository: UserRepository, sso_user_repository: SsoUserRepository
    ):
        self.user_repository = user_repository
        self.sso_user_repository = sso_user_repository

    def execute(self, command: GetUserMeCommand) -> GetUserMeResponse:
        user = self.user_repository.get_by_id(command.requesting_user_id)
        if user is None:
            raise UserNotFoundException(command.requesting_user_id)

        # Check if user is an SSO user
        sso_user = self.sso_user_repository.get_by_user_id(user.id)
        is_sso = sso_user is not None

        return GetUserMeResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            name=user.name,
            roles=user.roles,
            is_sso=is_sso,
        )
