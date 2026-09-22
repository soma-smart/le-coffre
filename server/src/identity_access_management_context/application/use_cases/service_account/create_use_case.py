from uuid import uuid4

from identity_access_management_context.application.commands import CreateServiceAccountCommand
from identity_access_management_context.application.gateways import (
    ServiceAccountEventRepository,
    ServiceAccountRepository,
)
from identity_access_management_context.application.responses import CreateServiceAccountResponse
from identity_access_management_context.application.services import GroupManagementPermissionService
from identity_access_management_context.domain.entities import ServiceAccount
from identity_access_management_context.domain.events import ServiceAccountCreatedEvent
from identity_access_management_context.domain.exceptions import (
    TooManyActiveServiceAccountsError,
)
from identity_access_management_context.domain.value_objects import ServiceAccountToken
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway

from ._use_case import ServiceAccountUseCase


class CreateServiceAccountUseCase(
    ServiceAccountUseCase[CreateServiceAccountCommand, ServiceAccountCreatedEvent, CreateServiceAccountResponse]
):
    _max_active_accounts: int

    def __init__(
        self,
        service_account_repository: ServiceAccountRepository,
        permission_service: GroupManagementPermissionService,
        event_publisher: DomainEventPublisher,
        service_account_event_repository: ServiceAccountEventRepository,
        time_provider: TimeGateway,
        max_active_accounts: int,
    ):
        super().__init__(
            service_account_repository,
            permission_service,
            event_publisher,
            service_account_event_repository,
            time_provider,
        )
        self._max_active_accounts = max_active_accounts

    def _execute(
        self, command: CreateServiceAccountCommand
    ) -> tuple[ServiceAccountCreatedEvent, CreateServiceAccountResponse]:
        # Check the user has the right permissions
        self._permissions.ensure_user_can_manage_group(command.requesting_user, command.group_id)

        # Check the service account name
        name = ServiceAccount.validated_service_account_name(command.name)

        # Retrieve active service accounts of the group
        active_service_accounts = list(filter(lambda a: a.is_active, self._repository.list_for_group(command.group_id)))

        # Check that there is not the maximum number of accounts created already
        if len(active_service_accounts) >= self._max_active_accounts:
            raise TooManyActiveServiceAccountsError(len(active_service_accounts), self._max_active_accounts)

        # Check that there is not the maximum number of accounts created already
        # NOTE: Not sure we want this
        # if any(account.name == name for account in active_service_accounts):
        #     raise ServiceAccountAlreadyExistsException(command.group_id, name)

        # Create the service account
        now = self._time_provider.get_current_time()
        token = ServiceAccountToken.generate()
        account = ServiceAccount.create(group_id=command.group_id, name=name, token=token)
        self._repository.create((account,))

        event = ServiceAccountCreatedEvent(
            event_id=uuid4(),
            occurred_on=now,
            user_id=command.requesting_user.user_id,
            service_account_id=account.id,
            service_account_name=account.name,
        )
        response = CreateServiceAccountResponse(
            id=account.id,
            group_id=account.group_id,
            name=account.name,
            token=token.value,
        )

        return event, response
