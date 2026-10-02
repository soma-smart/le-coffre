from typing import override
from uuid import uuid4

from identity_access_management_context.application.commands import RevokeServiceAccountCommand
from identity_access_management_context.application.gateways import (
    ServiceAccountEventRepository,
    ServiceAccountRepository,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.application.responses import RevokeServiceAccountResponse
from identity_access_management_context.application.services.service_account_permission_service import (
    ServiceAccountPermissionService,
)
from identity_access_management_context.domain.events import ServiceAccountRevokedEvent
from identity_access_management_context.domain.exceptions import (
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
)
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway

from ._use_case import ServiceAccountUseCase


class RevokeServiceAccountUseCase(
    ServiceAccountUseCase[RevokeServiceAccountCommand, ServiceAccountRevokedEvent, RevokeServiceAccountResponse]
):
    _token_credential_record_repository: TokenCredentialRecordRepository

    def __init__(
        self,
        service_account_repository: ServiceAccountRepository,
        token_credential_record_repository: TokenCredentialRecordRepository,
        permission_service: ServiceAccountPermissionService,
        event_publisher: DomainEventPublisher,
        service_account_event_repository: ServiceAccountEventRepository,
        time_provider: TimeGateway,
    ):
        super().__init__(
            service_account_repository,
            permission_service,
            event_publisher,
            service_account_event_repository,
            time_provider,
        )
        self._token_credential_record_repository = token_credential_record_repository

    @override
    def _execute(
        self, command: RevokeServiceAccountCommand
    ) -> tuple[ServiceAccountRevokedEvent, RevokeServiceAccountResponse]:
        # Retrieve the service account
        (account,) = self._repository.get_by_ids([command.service_account_id])
        if account is None:
            raise ServiceAccountNotFoundException(command.service_account_id)

        # Check the user has permission to manage the service account
        self._permissions.ensure_user_can_manage_group(command.requesting_user, account.group_id)

        # Check the service account is active
        if not account.is_active:
            raise ServiceAccountAlreadyRevokedException(account.id)

        # Revoke the service account
        now = self._time_provider.get_current_time()
        self._repository.revoke([account.id], now)
        # Without its token records, a revoked account can no longer authenticate.
        self._token_credential_record_repository.delete_by_principal_ids([account.id])

        event = ServiceAccountRevokedEvent(
            event_id=uuid4(),
            occurred_on=now,
            principal_id=command.requesting_user.user_id,
            service_account_id=account.id,
            service_account_name=account.name,
        )
        response = RevokeServiceAccountResponse(id=account.id)

        return event, response
