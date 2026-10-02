from identity_access_management_context.application.commands import GetUserMeCommand
from identity_access_management_context.application.gateways import (
    SSOCredentialRecordRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import GetUserMeResponse
from identity_access_management_context.domain.exceptions import UserNotFoundException
from shared_kernel.application.tracing import TracedUseCase


class GetUserMeUseCase(TracedUseCase):
    def __init__(
        self, user_repository: UserRepository, sso_credential_record_repository: SSOCredentialRecordRepository
    ):
        self.user_repository = user_repository
        self.sso_credential_record_repository = sso_credential_record_repository

    def execute(self, command: GetUserMeCommand) -> GetUserMeResponse:
        user = self.user_repository.get_by_id(command.requesting_user_id)
        if user is None:
            raise UserNotFoundException(command.requesting_user_id)

        is_sso = self.sso_credential_record_repository.get_by_principal_id(user.id) is not None

        return GetUserMeResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            name=user.name,
            roles=user.roles,
            is_sso=is_sso,
        )
