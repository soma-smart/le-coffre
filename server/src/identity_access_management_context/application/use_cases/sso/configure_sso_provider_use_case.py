from identity_access_management_context.application.gateways import SsoGateway
from identity_access_management_context.domain.exceptions import InvalidSsoSettingsException


class ConfigureSsoProviderUseCase:
    """
    Use case to configure SSO provider via OpenID Connect auto-discovery.

    This use case handles the complete SSO configuration flow by delegating
    the discovery and configuration to the SSO gateway.
    """

    def __init__(self, sso_gateway: SsoGateway):
        self._sso_gateway = sso_gateway

    async def execute(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> None:
        """
        Configure SSO provider via OpenID Connect auto-discovery.

        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            discovery_url: OpenID Connect discovery URL (.well-known/openid_configuration)

        Raises:
            InvalidSsoSettingsException: If required parameters are missing or discovery fails
        """
        if not all([client_id, client_secret, discovery_url]):
            raise InvalidSsoSettingsException(
                "Client ID, client secret, and discovery URL are required"
            )

        try:
            # Delegate discovery and configuration to the gateway
            await self._sso_gateway.configure_with_discovery(
                client_id=client_id,
                client_secret=client_secret,
                discovery_url=discovery_url,
            )

        except ValueError as e:
            raise InvalidSsoSettingsException(f"Auto-discovery failed: {str(e)}")
        except Exception as e:
            raise InvalidSsoSettingsException(f"Configuration failed: {str(e)}")
