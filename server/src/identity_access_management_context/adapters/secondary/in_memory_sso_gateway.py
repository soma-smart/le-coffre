from uuid import uuid4
from typing import Dict, Any
from identity_access_management_context.application.gateways import SsoGateway
from identity_access_management_context.domain.entities import SsoUser
from identity_access_management_context.domain.exceptions import InvalidSsoCodeException


class InMemorySSOGateway(SsoGateway):
    def __init__(
        self,
        authorize_url: str = "https://example.com/authorize",
        valid_codes: Dict[str, Dict[str, Any]] | None = None,
    ) -> None:
        self.authorize_url = authorize_url
        self._valid_codes = valid_codes or {}
        self._client_id = None
        self._client_secret = None
        self._authorization_endpoint = None
        self._token_endpoint = None
        self._userinfo_endpoint = None
        self._jwks_uri = None

    async def get_authorize_url(self) -> str:
        return self.authorize_url

    async def validate_callback(self, code: str) -> SsoUser:
        if code not in self._valid_codes:
            raise InvalidSsoCodeException(f"Invalid SSO code: {code}")

        user_data = self._valid_codes[code]

        return SsoUser(
            internal_user_id=uuid4(),  # Temporary - will be set properly by the use case
            email=user_data["email"],
            display_name=user_data["display_name"],
            sso_user_id=user_data["sso_user_id"],
            sso_provider=user_data["provider"],
        )

    def _configure(
        self,
        client_id: str,
        client_secret: str,
        authorization_endpoint: str,
        token_endpoint: str,
        userinfo_endpoint: str,
        jwks_uri: str = "",
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._authorization_endpoint = authorization_endpoint
        self._token_endpoint = token_endpoint
        self._userinfo_endpoint = userinfo_endpoint
        self._jwks_uri = jwks_uri

    async def configure_with_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> None:
        """
        Mock implementation of configure_with_discovery for testing.

        In real tests, this would simulate a successful discovery.
        """
        # Mock discovery response based on discovery_url
        if "google" in discovery_url:
            self._configure(
                client_id=client_id,
                client_secret=client_secret,
                authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
                token_endpoint="https://oauth2.googleapis.com/token",
                userinfo_endpoint="https://www.googleapis.com/oauth2/v2/userinfo",
                jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
            )
        elif "microsoft" in discovery_url:
            self._configure(
                client_id=client_id,
                client_secret=client_secret,
                authorization_endpoint="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                token_endpoint="https://login.microsoftonline.com/common/oauth2/v2.0/token",
                userinfo_endpoint="https://graph.microsoft.com/v1.0/me",
                jwks_uri="https://login.microsoftonline.com/common/discovery/v2.0/keys",
            )
        else:
            # Generic mock configuration
            self._configure(
                client_id=client_id,
                client_secret=client_secret,
                authorization_endpoint="https://example.com/oauth/authorize",
                token_endpoint="https://example.com/oauth/token",
                userinfo_endpoint="https://example.com/oauth/userinfo",
                jwks_uri="https://example.com/oauth/jwks",
            )
