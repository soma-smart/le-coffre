from uuid import uuid4

from identity_access_management_context.application.commands import RotateServiceAccountTokenCommand
from identity_access_management_context.application.responses import RotateServiceAccountTokenResponse
from identity_access_management_context.domain.events import ServiceAccountTokenRotatedEvent
from identity_access_management_context.domain.exceptions import (
    ServiceAccountAlreadyRevokedException,
    ServiceAccountNotFoundException,
)
from identity_access_management_context.domain.value_objects import ServiceAccountToken

from ._use_case import ServiceAccountUseCase


class RotateServiceAccountTokenUseCase(
    ServiceAccountUseCase[
        RotateServiceAccountTokenCommand, ServiceAccountTokenRotatedEvent, RotateServiceAccountTokenResponse
    ]
):
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
        self._repository.rotate((account.id,), (token.hash,))

        event = ServiceAccountTokenRotatedEvent(
            event_id=uuid4(),
            occurred_on=now,
            user_id=command.requesting_user.user_id,
            service_account_id=account.id,
            service_account_name=account.name,
        )
        response = RotateServiceAccountTokenResponse(id=account.id, token=token.value)

        return event, response
