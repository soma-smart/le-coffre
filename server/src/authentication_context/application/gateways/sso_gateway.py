from typing import Protocol
from authentication_context.domain.entities import SsoUser


class SsoGateway(Protocol):
    async def get_authorize_url(self) -> str: ...

    async def validate_callback(self, code: str) -> SsoUser: ...

    def set_settings(self, client_id: str, client_secret: str) -> None: ...
