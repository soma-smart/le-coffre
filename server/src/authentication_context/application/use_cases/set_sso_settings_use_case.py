from authentication_context.application.gateways import SsoGateway
from authentication_context.domain.exceptions import InvalidSsoSettingsException


class SsoSetSettingsUseCase:
    def __init__(self, sso_gateway: SsoGateway):
        self._sso_gateway = sso_gateway

    def execute(self, client_id: str, client_secret: str) -> None:
        if not client_id or not client_secret:
            raise InvalidSsoSettingsException("Client ID and secret are required")

        self._sso_gateway.set_settings(client_id=client_id, client_secret=client_secret)
