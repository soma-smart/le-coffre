from identity_access_management_context.application.commands import (
    GetSsoAuthorizeUrlCommand,
)
from identity_access_management_context.application.gateways import (
    SsoGateway,
    SsoConfigurationRepository,
)
from identity_access_management_context.application.services import (
    SsoConfigurationDecryptingService,
)
from shared_kernel.encryption import EncryptionService


class GetSsoAuthorizeUrlUseCase:
    def __init__(
        self,
        sso_gateway: SsoGateway,
        sso_configuration_repository: SsoConfigurationRepository,
        encryption_service: EncryptionService,
    ):
        self._sso_gateway = sso_gateway
        self._sso_configuration_repository = sso_configuration_repository
        self._encryption_service = encryption_service

    async def execute(self, command: GetSsoAuthorizeUrlCommand) -> str:
        sso_config = SsoConfigurationDecryptingService(
            self._sso_configuration_repository, self._encryption_service
        ).decrypt()

        return await self._sso_gateway.get_authorize_url(sso_config)
