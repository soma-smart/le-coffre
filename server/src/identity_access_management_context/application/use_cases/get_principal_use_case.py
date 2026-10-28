from identity_access_management_context.application.commands import GetPrincipalCommand
from identity_access_management_context.application.responses import GetPrincipalResponse
from shared_kernel.application.gateways import PrincipalRepository
from shared_kernel.application.tracing import TracedUseCase


class GetPrincipalUseCase(TracedUseCase):
    """Names a principal, whatever its kind, for whoever has to show it as an actor."""

    def __init__(self, principal_repository: PrincipalRepository):
        self._principal_repository = principal_repository

    def execute(self, command: GetPrincipalCommand) -> GetPrincipalResponse | None:
        principal = self._principal_repository.get_by_id(command.principal_id)
        if principal is None:
            return None
        return GetPrincipalResponse.of(principal)
