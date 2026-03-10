from identity_access_management_context.application.commands import (
    GetSsoAuthorizeUrlCommand,
)
from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
    SsoEncryptionGateway,
    SsoGateway,
)
from identity_access_management_context.application.services import (
    SsoConfigurationDecryptingService,
)
from shared_kernel.application.tracing import TracedUseCase


class GetSsoAuthorizeUrlUseCase(TracedUseCase):
    def __init__(
        self,
        sso_gateway: SsoGateway,
        sso_configuration_repository: SsoConfigurationRepository,
        sso_encryption_gateway: SsoEncryptionGateway,
    ):
        self._sso_gateway = sso_gateway
        self._sso_configuration_repository = sso_configuration_repository
        self._sso_encryption_gateway = sso_encryption_gateway

    async def execute(self, command: GetSsoAuthorizeUrlCommand) -> str:
        sso_config = SsoConfigurationDecryptingService(
            self._sso_configuration_repository, self._sso_encryption_gateway
        ).decrypt()

        return await self._sso_gateway.get_authorize_url(sso_config)
