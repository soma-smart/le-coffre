from typing import Any, Dict
import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client

from identity_access_management_context.application.gateways import (
    SsoGateway,
    SsoUserInfo,
    SsoDiscoveryResult,
)
from identity_access_management_context.domain.exceptions import InvalidSsoCodeException
from identity_access_management_context.domain.entities import SsoConfiguration
from urllib.parse import urlencode


class OAuth2SsoGateway(SsoGateway):
    """
    SSO Gateway implementation using OAuth2/OIDC protocol.

    Reads configuration from repository and uses encryption service for secrets.
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

    async def validate_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> SsoDiscoveryResult:
        """Validate SSO discovery configuration and return endpoints."""
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

                return SsoDiscoveryResult(
                    authorization_endpoint=config["authorization_endpoint"],
                    token_endpoint=config["token_endpoint"],
                    userinfo_endpoint=config.get("userinfo_endpoint", ""),
                    jwks_uri=config.get("jwks_uri", ""),
                )
        except httpx.TimeoutException:
            raise ValueError("Timeout in discovering endpoints")
        except httpx.HTTPStatusError as e:
            raise ValueError(f"HTTP error during discovery: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Error during discovery of endpoints: {str(e)}")

    def _get_oauth_client(self, config: SsoConfiguration) -> AsyncOAuth2Client:
        """Get or create the OAuth2 client from stored configuration."""
        # Decrypt the client secret before using it
        return AsyncOAuth2Client(
            client_id=config.client_id,
            client_secret=config.client_secret_decrypted,
            scope=self.scope,
            redirect_uri=self.redirect_uri,
        )

    async def get_authorize_url(self, config) -> str:
        """Generate OAuth2 authorization URL."""
        client = self._get_oauth_client(config)

        # Generate authorization URL with state parameter for security
        authorization_url, state = client.create_authorization_url(
            config.authorization_endpoint,
            state=client.token.get("state") if isinstance(client.token, dict) else None,
        )

        return authorization_url

    async def validate_callback(
        self, config: SsoConfiguration, code: str
    ) -> SsoUserInfo:
        """
        Validate OAuth2 authorization code and return user information.

        This method:
        1. Exchanges the authorization code for access token
        2. Fetches user information from the provider
        3. Returns a standardized SsoUserInfo object (provider data only)
        """

        client = self._get_oauth_client(config)

        try:
            # Exchange authorization code for access token
            auth_response = f"{self.redirect_uri}?{urlencode({'code': code})}"

            token = await client.fetch_token(
                config.token_endpoint,
                authorization_response=auth_response,
            )

            # Fetch user information
            async with httpx.AsyncClient() as http_client:
                # Set the token for authorized requests
                client.token = token

                # Use the client's session to make authenticated requests
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                resp = await http_client.get(config.userinfo_endpoint, headers=headers)
                resp.raise_for_status()
                user_info = resp.json()

            # Extract user information based on provider
            email = self._extract_email(user_info)
            display_name = self._extract_display_name(user_info)
            sso_user_id = self._extract_user_id(user_info)

            return SsoUserInfo(
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
