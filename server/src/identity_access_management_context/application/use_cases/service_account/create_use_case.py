from typing import override
from uuid import uuid4

from identity_access_management_context.application.commands import CreateServiceAccountCommand
from identity_access_management_context.application.gateways import (
    ServiceAccountEventRepository,
    ServiceAccountRepository,
    ServiceAccountTokenCredentialRecordRepository,
)
from identity_access_management_context.application.responses import CreateServiceAccountResponse
from identity_access_management_context.application.services import ServiceAccountPermissionService
from identity_access_management_context.domain.entities import ServiceAccount, ServiceAccountTokenCredentialRecord
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
    _token_credential_record_repository: ServiceAccountTokenCredentialRecordRepository

    def __init__(
        self,
        service_account_repository: ServiceAccountRepository,
        token_credential_record_repository: ServiceAccountTokenCredentialRecordRepository,
        permission_service: ServiceAccountPermissionService,
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
        self._token_credential_record_repository = token_credential_record_repository
        self._max_active_accounts = max_active_accounts

    @override
    def _execute(
        self, command: CreateServiceAccountCommand
    ) -> tuple[ServiceAccountCreatedEvent, CreateServiceAccountResponse]:
        # Check the user has the right permissions
        self._permissions.ensure_user_can_manage_group(command.requesting_user, command.group_id)

        # Check the service account name
        name = ServiceAccount.validated_service_account_name(command.name)

        # Retrieve active service accounts of the group
        group_accounts = self._repository.list_for_groups((command.group_id,))
        active_service_accounts = [account for account in group_accounts if account.is_active]

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
        account = ServiceAccount.create(group_id=command.group_id, name=name)
        self._repository.create((account,))
        self._token_credential_record_repository.create(
            (ServiceAccountTokenCredentialRecord(principal_id=account.id, token_hash=token.hash),)
        )

        event = ServiceAccountCreatedEvent(
            event_id=uuid4(),
            occurred_on=now,
            principal_id=command.requesting_user.user_id,
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
