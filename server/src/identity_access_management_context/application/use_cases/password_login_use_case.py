import asyncio
import logging

from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    PasswordHashingGateway,
    TokenGateway,
    UserPasswordRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import AdminLoginResponse
from identity_access_management_context.domain.events import (
    AdminLoginEvent,
    AdminLoginFailedEvent,
)
from identity_access_management_context.domain.exceptions import (
    AdminNotFoundException,
    InvalidCredentialsException,
)
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class PasswordLoginUseCase(TracedUseCase):
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        user_repository: UserRepository,
        password_hashing_gateway: PasswordHashingGateway,
        token_gateway: TokenGateway,
        time_provider: TimeGateway,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
    ):
        self._user_password_repository = user_password_repository
        self._user_repository = user_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._token_gateway = token_gateway
        self._time_provider = time_provider
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository

    async def execute(self, command: AdminLoginCommand) -> AdminLoginResponse:
        # DB reads and bcrypt verification are synchronous and blocking — run
        # them in a thread pool to avoid starving the event loop.
        def _lookup_and_verify():
            user_password = self._user_password_repository.get_by_email(command.email)
            if not user_password:
                logger.warning("Login failed for email=%s reason='User not found'", command.email)
                event = AdminLoginFailedEvent(email=command.email, reason="User not found")
                self._event_publisher.publish(event)
                self._admin_event_repository.append_event(
                    event_id=event.event_id,
                    event_type=type(event).__name__,
                    occurred_on=event.occurred_on,
                    actor_user_id=None,
                    event_data={"email": command.email, "reason": "User not found"},
                )
                raise AdminNotFoundException("User not found")

            if not self._password_hashing_gateway.verify(command.password, user_password.password_hash):
                logger.warning("Login failed for email=%s reason='Invalid credentials'", command.email)
                event = AdminLoginFailedEvent(email=command.email, reason="Invalid credentials")
                self._event_publisher.publish(event)
                self._admin_event_repository.append_event(
                    event_id=event.event_id,
                    event_type=type(event).__name__,
                    occurred_on=event.occurred_on,
                    actor_user_id=None,
                    event_data={"email": command.email, "reason": "Invalid credentials"},
                )
                raise InvalidCredentialsException("Invalid credentials")

            user = self._user_repository.get_by_id(user_password.id)
            roles = user.roles if user is not None else []
            return user_password, roles

        user_password, roles = await asyncio.to_thread(_lookup_and_verify)

        token = await self._token_gateway.generate_token(
            user_id=user_password.id,
            email=user_password.email,
            roles=roles,
            claims={"display_name": user_password.display_name},
        )

        refresh_token = await self._token_gateway.generate_refresh_token(
            user_id=user_password.id,
            email=user_password.email,
            roles=roles,
        )

        event = AdminLoginEvent(admin_id=user_password.id, email=user_password.email)
        self._event_publisher.publish(event)
        await asyncio.to_thread(
            lambda: self._admin_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=user_password.id,
                event_data={"email": user_password.email},
            )
        )

        return AdminLoginResponse(
            jwt_token=token.value,
            refresh_token=refresh_token,
            admin_id=user_password.id,
            email=user_password.email,
        )
