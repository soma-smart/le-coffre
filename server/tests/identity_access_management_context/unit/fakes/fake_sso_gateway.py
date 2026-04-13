from identity_access_management_context.application.gateways import (
    SsoDiscoveryResult,
    SsoGateway,
    SsoUserInfo,
)
from identity_access_management_context.domain.entities import SsoConfiguration
from identity_access_management_context.domain.exceptions import InvalidSsoCodeException


class FakeSsoGateway(SsoGateway):
    def __init__(self):
        self._authorize_url = ""
        self._valid_codes = {}  # code -> SsoUserInfo mapping
        self._discovery_error: Exception | None = None
        self._discovery_result: SsoDiscoveryResult | None = None

    async def get_authorize_url(self, config: SsoConfiguration) -> str:
        return self._authorize_url

    async def validate_callback(
        self, config: SsoConfiguration, code: str, redirect_uri: str | None = None
    ) -> SsoUserInfo:
        """Validate the SSO callback code and return user info"""
        if code not in self._valid_codes:
            raise InvalidSsoCodeException(f"Invalid SSO code: {code}")
        return self._valid_codes[code]

    async def validate_discovery(
        self,
        client_id: str,
        client_secret: str,
        discovery_url: str,
    ) -> SsoDiscoveryResult:
        """Validate SSO discovery configuration"""
        if self._discovery_error:
            raise self._discovery_error

        if self._discovery_result:
            return self._discovery_result

        # Default discovery result for tests
        return SsoDiscoveryResult(
            authorization_endpoint="https://provider.com/authorize",
            token_endpoint="https://provider.com/token",
            userinfo_endpoint="https://provider.com/userinfo",
            jwks_uri="https://provider.com/jwks",
        )

    def set_authorize_url(self, url: str) -> None:
        """Helper method for tests to set the URL that will be returned"""
        self._authorize_url = url

    def set_discovery_error(self, error: Exception) -> None:
        """Helper method for tests to set discovery error"""
        self._discovery_error = error

    def set_discovery_result(self, result: SsoDiscoveryResult) -> None:
        """Helper method for tests to set discovery result"""
        self._discovery_result = result

    ## Helpers for fake gateway

    def set_valid_code(self, code: str, user_info: SsoUserInfo) -> None:
        """Helper method for tests to set valid codes"""
        self._valid_codes[code] = user_info

    def clear_codes(self) -> None:
        """Helper method for tests to clear all codes"""
        self._valid_codes.clear()
