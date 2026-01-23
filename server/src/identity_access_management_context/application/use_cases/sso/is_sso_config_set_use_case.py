from identity_access_management_context.application.responses import (
    IsSsoConfigSetResponse,
)
from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
)


class IsSsoConfigSetUseCase:
    def __init__(self, sso_configuration_repository: SsoConfigurationRepository):
        self._sso_configuration_repository = sso_configuration_repository

    def execute(self) -> IsSsoConfigSetResponse:
        sso_config = self._sso_configuration_repository.get()
        is_set = sso_config is not None

        return IsSsoConfigSetResponse(is_set=is_set)
