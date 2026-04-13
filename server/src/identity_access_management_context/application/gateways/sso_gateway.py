from dataclasses import dataclass
from typing import Protocol

from identity_access_management_context.domain.entities import SsoConfiguration


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


@dataclass(frozen=True)
class SsoDiscoveryResult:
    """Result from SSO discovery validation."""

    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    jwks_uri: str | None = None


class SsoGateway(Protocol):
    async def get_authorize_url(self, config: SsoConfiguration) -> str: ...

    async def validate_callback(
        self, config: SsoConfiguration, code: str, redirect_uri: str | None = None
    ) -> SsoUserInfo: ...

    async def validate_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> SsoDiscoveryResult:
        """
        Validate SSO configuration by checking discovery URL.
        Returns discovery results if valid, raises ValueError if invalid.
        """
        ...
