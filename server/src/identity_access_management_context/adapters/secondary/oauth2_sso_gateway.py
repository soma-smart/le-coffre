import logging
from typing import Any
from urllib.parse import urlencode

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client

from identity_access_management_context.adapters.secondary.sso_url_validator import (
    SsoUrlValidator,
)
from identity_access_management_context.application.gateways import (
    SsoDiscoveryResult,
    SsoGateway,
    SsoUserInfo,
)
from identity_access_management_context.domain.entities import SsoConfiguration
from identity_access_management_context.domain.exceptions import (
    InvalidSsoCodeException,
    InvalidSsoSettingsException,
)

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT_SECONDS = 10.0


class OAuth2SsoGateway(SsoGateway):
    """
    SSO Gateway implementation using OAuth2/OIDC protocol.

    Reads configuration from repository and uses encryption service for secrets.
    """

    def __init__(
        self,
        redirect_uri: str,
        scope: str = "openid email profile",
        provider: str = "default",
        url_validator: SsoUrlValidator | None = None,
    ):
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.provider = provider
        self._url_validator = url_validator or SsoUrlValidator()

    async def validate_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> SsoDiscoveryResult:
        """Validate SSO discovery configuration and return endpoints."""
        self._url_validator.validate(discovery_url)

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS, follow_redirects=False) as client:
                response = await client.get(discovery_url)
                response.raise_for_status()
                config = response.json()
        except InvalidSsoSettingsException:
            raise
        except Exception as e:
            logger.warning("SSO discovery request failed for %s: %s", discovery_url, e)
            raise InvalidSsoSettingsException("Unable to retrieve the SSO discovery document") from e

        required_fields = ["authorization_endpoint", "token_endpoint"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise InvalidSsoSettingsException("The SSO discovery document is missing required fields")

        discovery_result = SsoDiscoveryResult(
            authorization_endpoint=config["authorization_endpoint"],
            token_endpoint=config["token_endpoint"],
            userinfo_endpoint=config.get("userinfo_endpoint", ""),
            jwks_uri=config.get("jwks_uri", ""),
        )

        for endpoint in (
            discovery_result.authorization_endpoint,
            discovery_result.token_endpoint,
            discovery_result.userinfo_endpoint,
            discovery_result.jwks_uri,
        ):
            if endpoint:
                self._url_validator.validate(endpoint)

        return discovery_result

    def _get_oauth_client(self, config: SsoConfiguration) -> AsyncOAuth2Client:
        """Get or create the OAuth2 client from stored configuration."""
        # Decrypt the client secret before using it
        return AsyncOAuth2Client(
            client_id=config.client_id,
            client_secret=config.client_secret_decrypted,
            scope=self.scope,
            redirect_uri=self.redirect_uri,
            timeout=_HTTP_TIMEOUT_SECONDS,
            follow_redirects=False,
        )

    async def get_authorize_url(self, config: SsoConfiguration, state: str | None = None) -> str:
        """Generate OAuth2 authorization URL."""
        client = self._get_oauth_client(config)

        # Generate authorization URL with a caller-provided state for CSRF protection
        authorization_url, _ = client.create_authorization_url(
            config.authorization_endpoint,
            state=state,
        )

        return authorization_url

    async def validate_callback(
        self, config: SsoConfiguration, code: str, redirect_uri: str | None = None
    ) -> SsoUserInfo:
        """
        Validate OAuth2 authorization code and return user information.

        This method:
        1. Exchanges the authorization code for access token
        2. Fetches user information from the provider
        3. Returns a standardized SsoUserInfo object (provider data only)

        Args:
            config: SSO configuration with client credentials and endpoints
            code: The authorization code from the SSO provider
            redirect_uri: Override redirect URI (for CLI auth flows using localhost).
                          If None, uses the server's default redirect_uri.
        """

        # Re-validate persisted endpoints before any outbound call (defense in depth:
        # configs stored before this guard existed, or DNS rebinding, must not reach internal hosts).
        self._url_validator.validate(config.token_endpoint)
        self._url_validator.validate(config.userinfo_endpoint)

        # Use override redirect_uri if provided (for CLI auth), otherwise use default
        effective_redirect_uri = redirect_uri or self.redirect_uri

        # Reuse the shared client construction logic, overriding redirect_uri if needed
        client = self._get_oauth_client(config)
        client.redirect_uri = effective_redirect_uri

        try:
            # Exchange authorization code for access token
            auth_response = f"{effective_redirect_uri}?{urlencode({'code': code})}"

            token = await client.fetch_token(
                config.token_endpoint,
                authorization_response=auth_response,
            )

            # Fetch user information
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT_SECONDS, follow_redirects=False) as http_client:
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

        except InvalidSsoCodeException:
            raise
        except Exception as e:
            logger.warning("SSO callback validation failed: %s", e)
            raise InvalidSsoCodeException("SSO authentication failed") from e

    def _extract_email(self, user_info: dict[str, Any]) -> str:
        """Extract email from user info based on provider."""
        # Common email fields across providers
        email_fields = ["email", "mail", "userPrincipalName"]

        for field in email_fields:
            if field in user_info and user_info[field]:
                return user_info[field]

        raise InvalidSsoCodeException("Email not found in user information")

    def _extract_display_name(self, user_info: dict[str, Any]) -> str:
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

    def _extract_user_id(self, user_info: dict[str, Any]) -> str:
        """Extract unique user ID from user info based on provider."""
        # Common ID fields across providers
        id_fields = ["sub", "id", "oid", "objectId"]

        for field in id_fields:
            if field in user_info and user_info[field]:
                return str(user_info[field])

        raise InvalidSsoCodeException("User ID not found in user information")
