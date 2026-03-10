from identity_access_management_context.application.commands import (
    IsSsoConfigSetCommand,
)
from identity_access_management_context.application.gateways import (
    SsoConfigurationRepository,
)
from identity_access_management_context.application.responses import (
    IsSsoConfigSetResponse,
)
from shared_kernel.application.tracing import TracedUseCase


class IsSsoConfigSetUseCase(TracedUseCase):
    def __init__(self, sso_configuration_repository: SsoConfigurationRepository):
        self._sso_configuration_repository = sso_configuration_repository

    def execute(self, command: IsSsoConfigSetCommand) -> IsSsoConfigSetResponse:
        sso_config = self._sso_configuration_repository.get()
        is_set = sso_config is not None

        return IsSsoConfigSetResponse(is_set=is_set)
