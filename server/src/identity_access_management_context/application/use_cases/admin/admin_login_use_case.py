from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.responses import AdminLoginResponse
from identity_access_management_context.application.gateways import (
    UserPasswordRepository,
    PasswordHashingGateway,
    TokenGateway,
    IamEventRepository,
)
from identity_access_management_context.domain.events import AdminLoginEvent, AdminLoginFailedEvent
from identity_access_management_context.domain.exceptions import (
    InvalidCredentialsException,
    AdminNotFoundException,
)
from shared_kernel.domain.value_objects.constants import ADMIN_ROLE
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway


class AdminLoginUseCase:
    def __init__(
        self,
        user_password_repository: UserPasswordRepository,
        password_hashing_gateway: PasswordHashingGateway,
        token_gateway: TokenGateway,
        time_provider: TimeGateway,
        event_publisher: DomainEventPublisher,
        iam_event_repository: IamEventRepository,
    ):
        self._user_password_repository = user_password_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._token_gateway = token_gateway
        self._time_provider = time_provider
        self._event_publisher = event_publisher
        self._iam_event_repository = iam_event_repository

    async def execute(self, command: AdminLoginCommand) -> AdminLoginResponse:
        user_password = self._user_password_repository.get_by_email(command.email)
        if not user_password:
            event = AdminLoginFailedEvent(email=command.email, reason="User not found")
            self._event_publisher.publish(event)
            self._iam_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=None,
                event_data={"email": command.email, "reason": "User not found"},
            )
            raise AdminNotFoundException("User not found")

        if not self._password_hashing_gateway.verify(
            command.password, user_password.password_hash
        ):
            event = AdminLoginFailedEvent(email=command.email, reason="Invalid credentials")
            self._event_publisher.publish(event)
            self._iam_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=None,
                event_data={"email": command.email, "reason": "Invalid credentials"},
            )
            raise InvalidCredentialsException("Invalid credentials")

        token = await self._token_gateway.generate_token(
            user_id=user_password.id,
            email=user_password.email,
            roles=[ADMIN_ROLE],
            claims={"display_name": user_password.display_name},
        )

        refresh_token = await self._token_gateway.generate_refresh_token(
            user_id=user_password.id,
            email=user_password.email,
            roles=[ADMIN_ROLE],
        )

        event = AdminLoginEvent(admin_id=user_password.id, email=user_password.email)
        self._event_publisher.publish(event)
        self._iam_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=user_password.id,
            event_data={"email": user_password.email},
        )

        return AdminLoginResponse(
            jwt_token=token.value,
            refresh_token=refresh_token,
            admin_id=user_password.id,
            email=user_password.email,
        )
