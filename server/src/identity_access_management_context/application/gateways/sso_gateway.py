from typing import Protocol
from dataclasses import dataclass


@dataclass(frozen=True)
class SsoUserInfo:
    """
    DTO representing user information returned from SSO provider.
    This is the contract between the gateway and use cases.
    """

    email: str
    display_name: str
    sso_user_id: str
    sso_provider: str


class SsoGateway(Protocol):
    async def get_authorize_url(self) -> str: ...

    async def validate_callback(self, code: str) -> SsoUserInfo: ...

    async def configure_with_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> None: ...
