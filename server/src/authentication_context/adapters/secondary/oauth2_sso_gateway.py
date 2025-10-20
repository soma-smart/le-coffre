from typing import Any, Dict
from uuid import uuid4
import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client

from authentication_context.application.gateways import SsoGateway
from authentication_context.domain.entities import SsoUser
from authentication_context.domain.exceptions import InvalidSsoCodeException
from urllib.parse import urlencode


class OAuth2SsoGateway(SsoGateway):
    """
    SSO Gateway implementation using OAuth2/OIDC protocol.

    Supports any OAuth2/OIDC provider through OpenID Connect auto-discovery.

    Example:
        gateway = OAuth2SsoGateway(base_url="...", redirect_uri="...")

        # Use ConfigureSsoProviderUseCase for auto-discovery
        use_case = ConfigureSsoProviderUseCase(gateway)
        await use_case.execute(
            client_id="your-client-id",
            client_secret="your-client-secret",
            discovery_url="https://accounts.google.com/.well-known/openid_configuration"
        )
    """

    def __init__(
        self,
        base_url: str,
        redirect_uri: str,
        scope: str = "openid email profile",
        provider: str = "default",
    ):
        self.base_url = base_url
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.provider = provider

        # OAuth2 configuration
        self._client_id = ""
        self._client_secret = ""
        self._authorization_endpoint = ""
        self._token_endpoint = ""
        self._userinfo_endpoint = ""
        self._jwks_uri = ""

        self._oauth_client: AsyncOAuth2Client | None = None

    def configure(
        self,
        client_id: str,
        client_secret: str,
        authorization_endpoint: str,
        token_endpoint: str,
        userinfo_endpoint: str,
        jwks_uri: str = "",
    ) -> None:
        """Configure OAuth2 client credentials and provider endpoints."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._authorization_endpoint = authorization_endpoint
        self._token_endpoint = token_endpoint
        self._userinfo_endpoint = userinfo_endpoint
        self._jwks_uri = jwks_uri
        self._oauth_client = None  # Reset client to pick up new credentials

    async def configure_with_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> None:
        """Configure OAuth2 client via OpenID Connect auto-discovery."""
        # Discover endpoints from OpenID Connect configuration
        config = await self._discover_endpoints(discovery_url)

        # Configure with discovered endpoints
        self.configure(
            client_id=client_id,
            client_secret=client_secret,
            authorization_endpoint=config["authorization_endpoint"],
            token_endpoint=config["token_endpoint"],
            userinfo_endpoint=config["userinfo_endpoint"],
            jwks_uri=config["jwks_uri"],
        )

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

    def _get_oauth_client(self) -> AsyncOAuth2Client:
        """Get or create the OAuth2 client."""
        if self._oauth_client is None:
            if not self._client_id or not self._client_secret:
                raise ValueError("Client ID and secret must be configured")

            self._oauth_client = AsyncOAuth2Client(
                client_id=self._client_id,
                client_secret=self._client_secret,
                scope=self.scope,
                redirect_uri=self.redirect_uri,
            )

        return self._oauth_client

    async def get_authorize_url(self) -> str:
        """Generate OAuth2 authorization URL."""
        if not self._authorization_endpoint:
            raise ValueError("Authorization endpoint not configured")

        client = self._get_oauth_client()

        # Generate authorization URL with state parameter for security
        authorization_url, state = client.create_authorization_url(
            self._authorization_endpoint,
            state=client.token.get("state") if isinstance(client.token, dict) else None,
        )

        return authorization_url

    async def validate_callback(self, code: str) -> SsoUser:
        """
        Validate OAuth2 authorization code and return user information.

        This method:
        1. Exchanges the authorization code for access token
        2. Fetches user information from the provider
        3. Returns a standardized SsoUser object
        """
        if not self._token_endpoint or not self._userinfo_endpoint:
            raise ValueError("Token and userinfo endpoints not configured")

        client = self._get_oauth_client()

        try:
            # Exchange authorization code for access token
            async with httpx.AsyncClient() as http_client:
                auth_response = f"{self.redirect_uri}?{urlencode({'code': code})}"

                token = await client.fetch_token(
                    self._token_endpoint,
                    authorization_response=auth_response,
                    client=http_client,
                )

            # Fetch user information
            async with httpx.AsyncClient() as http_client:
                # Set the token for authorized requests
                client.token = token

                # Use the client's session to make authenticated requests
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                resp = await http_client.get(self._userinfo_endpoint, headers=headers)
                resp.raise_for_status()
                user_info = resp.json()

            # Extract user information based on provider
            email = self._extract_email(user_info)
            display_name = self._extract_display_name(user_info)
            sso_user_id = self._extract_user_id(user_info)

            return SsoUser(
                internal_user_id=uuid4(),  # Temporary - will be set by use case
                email=email,
                display_name=display_name,
                sso_user_id=sso_user_id,
                sso_provider=self.provider,
            )

        except Exception as e:
            raise InvalidSsoCodeException(f"Failed to validate SSO code: {str(e)}")

    def _extract_email(self, user_info: Dict[str, Any]) -> str:
        """Extract email from user info based on provider."""
        # Common email fields across providers
        email_fields = ["email", "mail", "userPrincipalName"]

        for field in email_fields:
            if field in user_info and user_info[field]:
                return user_info[field]

        raise InvalidSsoCodeException("Email not found in user information")

    def _extract_display_name(self, user_info: Dict[str, Any]) -> str:
        """Extract display name from user info based on provider."""
        # Try different name fields
        if "name" in user_info and user_info["name"]:
            return user_info["name"]

        if "displayName" in user_info and user_info["displayName"]:
            return user_info["displayName"]

        # Fallback: construct from first/last name
        first_name = user_info.get("given_name", user_info.get("givenName", ""))
        last_name = user_info.get("family_name", user_info.get("surname", ""))

        if first_name or last_name:
            return f"{first_name} {last_name}".strip()

        # Ultimate fallback: use email
        return self._extract_email(user_info)

    def _extract_user_id(self, user_info: Dict[str, Any]) -> str:
        """Extract unique user ID from user info based on provider."""
        # Common ID fields across providers
        id_fields = ["sub", "id", "oid", "objectId"]

        for field in id_fields:
            if field in user_info and user_info[field]:
                return str(user_info[field])

        raise InvalidSsoCodeException("User ID not found in user information")
