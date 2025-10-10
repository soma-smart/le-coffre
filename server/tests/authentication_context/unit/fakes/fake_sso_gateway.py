from authentication_context.domain.entities import SsoUser
from authentication_context.domain.exceptions import InvalidSsoCodeException


class FakeSsoGateway:
    def __init__(self):
        self._authorize_url = ""
        self._valid_codes = {}  # code -> SsoUser mapping
        self._client_id = ""
        self._client_secret = ""

    async def get_authorize_url(self) -> str:
        return self._authorize_url

    def set_authorize_url(self, url: str) -> None:
        """Helper method for tests to set the URL that will be returned"""
        self._authorize_url = url

    async def validate_callback(self, code: str) -> SsoUser:
        """Validate the SSO callback code and return user info"""
        if code not in self._valid_codes:
            raise InvalidSsoCodeException(f"Invalid SSO code: {code}")
        return self._valid_codes[code]

    def set_settings(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def set_valid_code(self, code: str, user_info: SsoUser) -> None:
        """Helper method for tests to set valid codes"""
        self._valid_codes[code] = user_info

    def clear_codes(self) -> None:
        """Helper method for tests to clear all codes"""
        self._valid_codes.clear()
