from uuid import uuid4

from identity_access_management_context.application.commands import RevokeServiceAccountCommand
from identity_access_management_context.application.responses import RevokeServiceAccountResponse
from identity_access_management_context.domain.events import ServiceAccountRevokedEvent
from identity_access_management_context.domain.exceptions import (
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
)

from ._use_case import ServiceAccountUseCase


class RevokeServiceAccountUseCase(
    ServiceAccountUseCase[RevokeServiceAccountCommand, ServiceAccountRevokedEvent, RevokeServiceAccountResponse]
):
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

        event = ServiceAccountRevokedEvent(
            event_id=uuid4(),
            occurred_on=now,
            user_id=command.requesting_user.user_id,
            service_account_id=account.id,
            service_account_name=account.name,
        )
        response = RevokeServiceAccountResponse(id=account.id)

        return event, response
