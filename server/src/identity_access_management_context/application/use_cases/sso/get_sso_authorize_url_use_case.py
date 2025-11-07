from identity_access_management_context.application.gateways import SsoGateway


class GetSsoAuthorizeUrlUseCase:
    def __init__(self, sso_gateway: SsoGateway):
        self._sso_gateway = sso_gateway

    async def execute(self) -> str:
        return await self._sso_gateway.get_authorize_url()
