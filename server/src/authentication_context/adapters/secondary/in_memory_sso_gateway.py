from uuid import uuid4
from typing import Dict, Any
from authentication_context.application.gateways import SsoGateway
from authentication_context.domain.entities import SsoUser
from authentication_context.domain.exceptions import InvalidSsoCodeException


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

    def configure(
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
