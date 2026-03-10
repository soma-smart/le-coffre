from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
    SsoEncryptionGateway,
)
from identity_access_management_context.domain.entities import SsoConfiguration


class SsoConfigurationDecryptingService:
    def __init__(
        self,
        sso_configuration_repository: SsoConfigurationRepository,
        sso_encryption_gateway: SsoEncryptionGateway,
    ):
        self._sso_configuration_repository = sso_configuration_repository
        self._sso_encryption_gateway = sso_encryption_gateway

    def decrypt(self) -> SsoConfiguration:
        sso_config = self._sso_configuration_repository.get()
        if not sso_config:
            raise ValueError("SSO configuration not found")

        sso_config.client_secret_decrypted = self._sso_encryption_gateway.decrypt(sso_config.client_secret)
        return sso_config
