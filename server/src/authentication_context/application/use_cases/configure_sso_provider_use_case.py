import httpx
from authentication_context.application.gateways import SsoGateway
from authentication_context.domain.exceptions import InvalidSsoSettingsException


class ConfigureSsoProviderUseCase:
    """
    Use case to configure SSO provider via OpenID Connect auto-discovery.

    This use case handles the complete SSO configuration flow:
    1. Discovers endpoints from OpenID Connect configuration URL
    2. Configures the SSO gateway with discovered endpoints and credentials
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
            # Discover endpoints from OpenID Connect configuration
            config = await self._discover_endpoints(discovery_url)

            # Configure the gateway with discovered endpoints
            self._sso_gateway.configure(
                client_id=client_id,
                client_secret=client_secret,
                authorization_endpoint=config["authorization_endpoint"],
                token_endpoint=config["token_endpoint"],
                userinfo_endpoint=config["userinfo_endpoint"],
                jwks_uri=config["jwks_uri"],
            )

        except ValueError as e:
            raise InvalidSsoSettingsException(f"Auto-discovery failed: {str(e)}")
        except Exception as e:
            raise InvalidSsoSettingsException(f"Configuration failed: {str(e)}")

    async def _discover_endpoints(self, discovery_url: str) -> dict:
        """Discover OpenID Connect endpoints from configuration URL."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(discovery_url)
                response.raise_for_status()
                config = response.json()

                # Validate required fields
                required_fields = ["authorization_endpoint", "token_endpoint"]
                missing_fields = [
                    field for field in required_fields if field not in config
                ]
                if missing_fields:
                    raise ValueError(f"Missing fields in discovery: {missing_fields}")

                return {
                    "authorization_endpoint": config["authorization_endpoint"],
                    "token_endpoint": config["token_endpoint"],
                    "userinfo_endpoint": config.get("userinfo_endpoint", ""),
                    "jwks_uri": config.get("jwks_uri", ""),
                }
        except httpx.TimeoutException:
            raise ValueError("Timeout in discovering endpoints")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error during discovery: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Error during discovery of endpoints: {str(e)}")
