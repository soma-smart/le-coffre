import asyncio
import logging
from datetime import datetime

from identity_access_management_context.application.commands import AdminLoginCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    LoginLockoutGateway,
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
    AccountLockedException,
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
        login_lockout_gateway: LoginLockoutGateway,
    ):
        self._user_password_repository = user_password_repository
        self._user_repository = user_repository
        self._password_hashing_gateway = password_hashing_gateway
        self._token_gateway = token_gateway
        self._time_provider = time_provider
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository
        self._login_lockout_gateway = login_lockout_gateway

    async def execute(self, command: AdminLoginCommand) -> AdminLoginResponse:
        now = self._time_provider.get_current_time()

        # Gate on lockout BEFORE touching the repository or bcrypt — a locked
        # account's latency must match any other 401 so the response time does
        # not leak account state.
        lockout_status = self._login_lockout_gateway.is_locked(command.email, now)
        if lockout_status is not None:
            logger.warning("Login blocked for email=%s reason='Account locked'", command.email)
            event = AdminLoginFailedEvent(email=command.email, reason="Account locked")
            self._event_publisher.publish(event)
            self._admin_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=None,
                event_data={"email": command.email, "reason": "Account locked"},
            )
            raise AccountLockedException(retry_after_seconds=lockout_status.retry_after_seconds)

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
                self._try_record_failed_login(command.email, now)
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
                self._try_record_failed_login(command.email, now)
                raise InvalidCredentialsException("Invalid credentials")

            user = self._user_repository.get_by_id(user_password.id)
            roles = user.roles if user is not None else []
            return user_password, roles

        user_password, roles = await asyncio.to_thread(_lookup_and_verify)

        self._try_record_successful_login(user_password.email)

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

    def _try_record_failed_login(self, email: str, now: datetime) -> None:
        """Increment the lockout counter, swallowing gateway outages.

        A broken counter write (future SQL/Redis adapter under load) must not
        replace the InvalidCredentialsException/AdminNotFoundException the
        route maps to 401: otherwise the attacker sees a 500 that leaks
        "brute-force defense is down", and the counter outage would become an
        enumeration oracle. The per-IP auth-route floor in RateLimitMiddleware
        still caps total attempts per IP even when this counter is unavailable.
        """
        try:
            self._login_lockout_gateway.record_failed_login(email, now)
        except Exception:  # noqa: BLE001 - fail-closed to the route's 401 mapping, alert ops via ERROR
            logger.error(
                "Lockout counter write failed on record_failed_login for email=%s; "
                "brute-force defense is degraded for this request. The /auth/login "
                "auth-route floor (per-IP) still caps attempts.",
                email,
                exc_info=True,
            )

    def _try_record_successful_login(self, email: str) -> None:
        """Clear the lockout counter; swallow outages so a counter blip doesn't gate token issuance."""
        try:
            self._login_lockout_gateway.record_successful_login(email)
        except Exception:  # noqa: BLE001 - availability over strict counter consistency here
            logger.error(
                "Lockout counter reset failed on record_successful_login for email=%s; "
                "proceeding with token issuance to avoid turning a counter-store outage "
                "into a full login outage.",
                email,
                exc_info=True,
            )
