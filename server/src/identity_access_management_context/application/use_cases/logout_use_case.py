import logging

from identity_access_management_context.application.gateways import (
    TokenGateway,
    AdminEventRepository,
)
from identity_access_management_context.domain.events import UserLoggedOutEvent
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.domain.entities import ValidatedUser

logger = logging.getLogger(__name__)


class LogoutUseCase:
    def __init__(
        self,
        token_gateway: TokenGateway,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
    ):
        self._token_gateway = token_gateway
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository

    async def execute(self, current_user: ValidatedUser, refresh_token: str | None) -> None:
        # Revoke the refresh token server-side if one was provided
        if refresh_token:
            await self._token_gateway.revoke_refresh_token(refresh_token)

        # Emit and persist a logout audit event
        event = UserLoggedOutEvent(
            user_id=current_user.user_id,
            email=current_user.email,
        )
        self._event_publisher.publish(event)
        self._admin_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=current_user.user_id,
            event_data={"email": current_user.email},
        )
