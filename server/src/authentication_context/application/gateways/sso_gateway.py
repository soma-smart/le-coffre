from typing import Protocol
from authentication_context.domain.entities import SsoUser


class SsoGateway(Protocol):
    async def get_authorize_url(self) -> str: ...

    async def validate_callback(self, code: str) -> SsoUser: ...

    def configure(
        self,
        client_id: str,
        client_secret: str,
        authorization_endpoint: str,
        token_endpoint: str,
        userinfo_endpoint: str,
        jwks_uri: str = "",
    ) -> None: ...

    async def configure_with_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> None: ...
