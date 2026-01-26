from datetime import datetime, timezone

from identity_access_management_context.application.commands import (
    ConfigureSsoProviderCommand,
)
from identity_access_management_context.application.gateways import (
    SsoGateway,
    SsoConfigurationRepository,
)
from identity_access_management_context.domain.entities import SsoConfiguration
from identity_access_management_context.domain.exceptions import (
    InvalidSsoSettingsException,
)
from shared_kernel.authentication import AdminPermissionChecker
from shared_kernel.encryption import EncryptionService


class ConfigureSsoProviderUseCase:
    """
    Use case to configure SSO provider via OpenID Connect auto-discovery.

    This use case:
    1. Validates the SSO configuration via the gateway
    2. Encrypts the client secret
    3. Stores the configuration via the repository
    """

    def __init__(
        self,
        sso_gateway: SsoGateway,
        sso_configuration_repository: SsoConfigurationRepository,
        encryption_service: EncryptionService,
    ):
        self._sso_gateway = sso_gateway
        self._sso_configuration_repository = sso_configuration_repository
        self._encryption_service = encryption_service

    async def execute(self, command: ConfigureSsoProviderCommand) -> None:
        """
        Configure SSO provider via OpenID Connect auto-discovery.

        Args:
            command: Contains requesting_user, client_id, client_secret, and discovery_url

        Raises:
            InvalidSsoSettingsException: If required parameters are missing or discovery fails
        """
        AdminPermissionChecker().ensure_admin(
            command.requesting_user, "configure SSO provider"
        )

        if not all(
            [command.client_id, command.client_secret, command.discovery_url]
        ):
            raise InvalidSsoSettingsException(
                "Client ID, client secret, and discovery URL are required"
            )

        try:
            # Step 1: Validate discovery with the gateway
            discovery_result = await self._sso_gateway.validate_discovery(
                client_id=command.client_id,
                client_secret=command.client_secret,
                discovery_url=command.discovery_url,
            )

            # Step 2: Encrypt the client secret
            encrypted_client_secret = self._encryption_service.encrypt(
                command.client_secret
            )

            # Step 3: Store the configuration
            config = SsoConfiguration(
                client_id=command.client_id,
                client_secret=encrypted_client_secret,
                discovery_url=command.discovery_url,
                authorization_endpoint=discovery_result.authorization_endpoint,
                token_endpoint=discovery_result.token_endpoint,
                userinfo_endpoint=discovery_result.userinfo_endpoint,
                jwks_uri=discovery_result.jwks_uri,
                updated_at=datetime.now(timezone.utc),
            )
            self._sso_configuration_repository.save(config)

        except ValueError as e:
            raise InvalidSsoSettingsException(f"Auto-discovery failed: {str(e)}")
        except Exception as e:
            raise InvalidSsoSettingsException(f"Configuration failed: {str(e)}")
