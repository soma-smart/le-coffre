from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
)
from identity_access_management_context.domain.entities import SsoConfiguration
from shared_kernel.encryption import EncryptionService


class SsoConfigurationDecryptingService:
    def __init__(
        self,
        sso_configuration_repository: SsoConfigurationRepository,
        encryption_service: EncryptionService,
    ):
        self._sso_configuration_repository = sso_configuration_repository
        self._encryption_service = encryption_service

    def decrypt(self) -> SsoConfiguration:
        sso_config = self._sso_configuration_repository.get()
        if not sso_config:
            raise ValueError("SSO configuration not found")

        sso_config.client_secret_decrypted = self._encryption_service.decrypt(
            sso_config.client_secret
        )
        return sso_config
