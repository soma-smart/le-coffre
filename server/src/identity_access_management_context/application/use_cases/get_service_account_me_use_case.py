from identity_access_management_context.application.commands import GetServiceAccountMeCommand
from identity_access_management_context.application.gateways import GroupRepository, ServiceAccountRepository
from identity_access_management_context.application.responses import GetServiceAccountMeResponse
from identity_access_management_context.domain.exceptions import (
    GroupNotFoundException,
    ServiceAccountNotFoundException,
)
from shared_kernel.application.tracing import TracedUseCase


class GetServiceAccountMeUseCase(TracedUseCase):
    """Tells a service account who it is: which account its token proves, for which group.

    What an operator calls to check a token works once plugged in. It reveals
    nothing the token does not already open.
    """

    def __init__(self, service_account_repository: ServiceAccountRepository, group_repository: GroupRepository):
        self._service_account_repository = service_account_repository
        self._group_repository = group_repository

    def execute(self, command: GetServiceAccountMeCommand) -> GetServiceAccountMeResponse:
        (service_account,) = self._service_account_repository.get_by_ids([command.service_account_id])
        if service_account is None:
            raise ServiceAccountNotFoundException(command.service_account_id)

        group = self._group_repository.get_by_id(service_account.group_id)
        if group is None:
            raise GroupNotFoundException(service_account.group_id)

        return GetServiceAccountMeResponse(
            service_account_id=service_account.id,
            name=service_account.name,
            group_id=group.id,
            group_name=group.name,
        )
