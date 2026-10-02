from typing import override
from uuid import uuid4

from identity_access_management_context.application.commands import RotateServiceAccountTokenCommand
from identity_access_management_context.application.gateways import (
    ServiceAccountEventRepository,
    ServiceAccountRepository,
    ServiceAccountTokenCredentialRecordRepository,
)
from identity_access_management_context.application.responses import RotateServiceAccountTokenResponse
from identity_access_management_context.application.services import ServiceAccountPermissionService
from identity_access_management_context.domain.entities import ServiceAccountTokenCredentialRecord
from identity_access_management_context.domain.events import ServiceAccountTokenRotatedEvent
from identity_access_management_context.domain.exceptions import (
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
)
from identity_access_management_context.domain.value_objects import ServiceAccountToken
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway

from ._use_case import ServiceAccountUseCase


class RotateServiceAccountTokenUseCase(
    ServiceAccountUseCase[
        RotateServiceAccountTokenCommand, ServiceAccountTokenRotatedEvent, RotateServiceAccountTokenResponse
    ]
):
    _token_credential_record_repository: ServiceAccountTokenCredentialRecordRepository

    def __init__(
        self,
        service_account_repository: ServiceAccountRepository,
        token_credential_record_repository: ServiceAccountTokenCredentialRecordRepository,
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
        self, command: RotateServiceAccountTokenCommand
    ) -> tuple[ServiceAccountTokenRotatedEvent, RotateServiceAccountTokenResponse]:
        # Retrieve the service account
        (account,) = self._repository.get_by_ids([command.service_account_id])
        if account is None:
            raise ServiceAccountNotFoundException(command.service_account_id)

        # Check the user has permission to manage the service account
        self._permissions.ensure_user_can_manage_group(command.requesting_user, account.group_id)

        # Check the service account is active
        if not account.is_active:
            raise ServiceAccountAlreadyRevokedException(account.id)

        # Rotate the token
        now = self._time_provider.get_current_time()
        token = ServiceAccountToken.generate()
        self._token_credential_record_repository.replace(
            (ServiceAccountTokenCredentialRecord(principal_id=account.id, token_hash=token.hash),)
        )

        event = ServiceAccountTokenRotatedEvent(
            event_id=uuid4(),
            occurred_on=now,
            user_id=command.requesting_user.user_id,
            service_account_id=account.id,
            service_account_name=account.name,
        )
        response = RotateServiceAccountTokenResponse(id=account.id, token=token.value)

        return event, response
