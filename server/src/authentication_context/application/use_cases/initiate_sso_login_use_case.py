from authentication_context.application.responses import InitiateSSOLoginResponse
from authentication_context.application.gateways import (
    SSOProviderGateway,
    StateGenerationGateway,
)


class InitiateSSOLoginUseCase:
    def __init__(
        self,
        sso_provider_gateway: SSOProviderGateway,
        state_generation_gateway: StateGenerationGateway,
    ):
        self.sso_provider_gateway = sso_provider_gateway
        self.state_generation_gateway = state_generation_gateway

    async def execute(self) -> InitiateSSOLoginResponse:
        state = self.state_generation_gateway.generate_state()

        authorization_url = await self.sso_provider_gateway.get_authorization_url(state)

        return InitiateSSOLoginResponse(
            authorization_url=authorization_url, state=state
        )
