from typing import override
from uuid import uuid4

from identity_access_management_context.application.commands import RotateServiceAccountTokenCommand
from identity_access_management_context.application.gateways import (
    CannotRotateTokenCredentialError,
    ServiceAccountEventRepository,
    ServiceAccountRepository,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.application.responses import RotateServiceAccountTokenResponse
from identity_access_management_context.application.services import ServiceAccountPermissionService
from identity_access_management_context.domain.events import ServiceAccountTokenRotatedEvent
from identity_access_management_context.domain.exceptions import (
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
)
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway

from ._use_case import ServiceAccountUseCase

# TODO: Rotate tokens instead, a service account may have multiple tokens


class RotateServiceAccountTokenUseCase(
    ServiceAccountUseCase[
        RotateServiceAccountTokenCommand, ServiceAccountTokenRotatedEvent, RotateServiceAccountTokenResponse
    ]
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

        # Retrieve tokens
        credential_records = self._token_credential_record_repository.list_by_principal_ids((account.id,))
        if not credential_records:
            # The account was revoked since the check above
            raise ServiceAccountAlreadyRevokedException(account.id)

        now = self._time_provider.get_current_time()

        # Rotate the tokens: generate new ones, then store their hashes in place of the old ones
        new_tokens = [TokenCredential.generate() for _ in credential_records]
        try:
            self._token_credential_record_repository.replace_token_hashes(
                (credential_record.token_hash for credential_record in credential_records),
                (token.hash for token in new_tokens),
            )
        except CannotRotateTokenCredentialError as e:
            raise ServiceAccountAlreadyRevokedException(account.id) from e

        # The response carries a single token: an account holds one until several can be issued
        (token,) = (token.value for token in new_tokens)

        event = ServiceAccountTokenRotatedEvent(
            event_id=uuid4(),
            occurred_on=now,
            principal_id=command.requesting_user.user_id,
            service_account_id=account.id,
            service_account_name=account.name,
        )
        response = RotateServiceAccountTokenResponse(id=account.id, token=token)

        return event, response
