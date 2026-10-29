import logging
from datetime import timedelta

from identity_access_management_context.application.commands import AuthenticateTokenCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.application.responses import AuthenticateTokenResponse
from identity_access_management_context.application.services.authentication import TokenAuthenticator
from identity_access_management_context.domain.entities import ServiceAccount, User
from identity_access_management_context.domain.events import TokenAuthenticationFailedEvent
from identity_access_management_context.domain.exceptions import (
    InvalidTokenCredentialError,
    TokenAuthenticationError,
)
from identity_access_management_context.domain.exceptions import (
    TokenAuthenticationFailureReason as Reason,
)
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.exceptions import OrphanedCredentialError, RejectedCredentialError, UnknownCredentialError

logger = logging.getLogger(__name__)


class AuthenticateTokenUseCase(TracedUseCase):
    """Resolves a presented token to the principal it proves, whatever its kind.

    Raises:
        TokenAuthenticationError: for a missing, malformed, unknown, expired or
            idle token, for a principal of another kind than required, or for an
            inactive service account. Only its reason differs, and errors are
            re-raised `from None` so the presented value never travels in a
            traceback.
    """

    def __init__(
        self,
        token_authenticator: TokenAuthenticator,
        token_credential_record_repository: TokenCredentialRecordRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
        last_used_coarsening_seconds: int,
    ):
        self._token_authenticator = token_authenticator
        self._token_credential_record_repository = token_credential_record_repository
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository
        self._time_provider = time_provider
        self._last_used_coarsening = timedelta(seconds=last_used_coarsening_seconds)

    def execute(self, command: AuthenticateTokenCommand) -> AuthenticateTokenResponse:
        try:
            return self._authenticate(command)
        except TokenAuthenticationError as error:
            self._record_failure(error, command.client_ip)
            raise

    def _record_failure(self, error: TokenAuthenticationError, client_ip: str | None) -> None:
        # A token has no lockout to fall back on: this trail is what shows someone
        # trying a leaked or guessed token.
        event = TokenAuthenticationFailedEvent(
            reason=error.reason,
            client_ip=client_ip or "unknown",
            occurred_on=self._time_provider.get_current_time(),
            principal_id=error.principal_id,
        )
        logger.warning("Token authentication failed reason='%s' client_ip=%s", error.reason.value, client_ip)
        self._event_publisher.publish(event)
        self._admin_event_repository.append_event(
            event_id=event.event_id,
            event_type=event.event_type,
            occurred_on=event.occurred_on,
            actor_principal_id=None,
            event_data=event.event_data,
        )

    def _authenticate(self, command: AuthenticateTokenCommand) -> AuthenticateTokenResponse:
        if command.token is None:
            raise TokenAuthenticationError(Reason.MISSING_TOKEN)
        try:
            token = TokenCredential(value=command.token)
        except InvalidTokenCredentialError:
            raise TokenAuthenticationError(Reason.MALFORMED_TOKEN) from None
        try:
            principal, credential_record = self._token_authenticator.authenticate_with_record(token)
        except RejectedCredentialError:
            raise TokenAuthenticationError(Reason.UNUSABLE_TOKEN) from None
        except (UnknownCredentialError, OrphanedCredentialError):
            raise TokenAuthenticationError(Reason.UNKNOWN_TOKEN) from None

        kind = "user" if isinstance(principal, User) else "service_account"
        if command.required_kind is not None and kind != command.required_kind:
            raise TokenAuthenticationError(Reason.PRINCIPAL_NOT_ALLOWED, principal.id)
        # Revoking deletes the account's tokens, this only guards a revocation that failed halfway.
        if isinstance(principal, ServiceAccount) and not principal.is_active:
            raise TokenAuthenticationError(Reason.INACTIVE_PRINCIPAL, principal.id)

        # Best-effort: recording the use must never fail an authentication that succeeded.
        try:
            self._token_credential_record_repository.touch_last_used(
                credential_record.id, self._time_provider.get_current_time(), self._last_used_coarsening
            )
        except Exception:  # noqa: BLE001
            logger.warning("Could not record the use of a token credential", exc_info=True)

        return AuthenticateTokenResponse(
            principal_id=principal.id,
            principal_kind=kind,
            roles=list(principal.roles) if isinstance(principal, User) else [],
            credential_id=credential_record.id,
            read_only=credential_record.read_only,
        )
