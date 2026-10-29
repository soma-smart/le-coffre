import logging
from datetime import timedelta

from identity_access_management_context.application.commands import AuthenticateTokenCommand
from identity_access_management_context.application.gateways import TokenCredentialRecordRepository
from identity_access_management_context.application.responses import AuthenticateTokenResponse
from identity_access_management_context.application.services.authentication import TokenAuthenticator
from identity_access_management_context.domain.entities import User
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class AuthenticateTokenUseCase(TracedUseCase):
    """Resolves a presented token to the principal it proves, whatever its kind.

    Raises:
        CredentialAuthenticationError: for a malformed, unknown, expired or idle token, or
            one whose principal is gone. The caller answers all of them the same
            way, so a token holder cannot tell which happened.
    """

    def __init__(
        self,
        token_authenticator: TokenAuthenticator,
        token_credential_record_repository: TokenCredentialRecordRepository,
        time_provider: TimeGateway,
        last_used_coarsening_seconds: int,
    ):
        self._token_authenticator = token_authenticator
        self._token_credential_record_repository = token_credential_record_repository
        self._time_provider = time_provider
        self._last_used_coarsening = timedelta(seconds=last_used_coarsening_seconds)

    def execute(self, command: AuthenticateTokenCommand) -> AuthenticateTokenResponse:
        principal, credential_record = self._token_authenticator.authenticate_with_record(
            TokenCredential(value=command.token)
        )

        # Best-effort: recording the use must never fail an authentication that succeeded.
        try:
            self._token_credential_record_repository.touch_last_used(
                credential_record.id, self._time_provider.get_current_time(), self._last_used_coarsening
            )
        except Exception:  # noqa: BLE001
            logger.warning("Could not record the use of a token credential", exc_info=True)

        is_user = isinstance(principal, User)
        return AuthenticateTokenResponse(
            principal_id=principal.id,
            principal_kind="user" if is_user else "service_account",
            roles=list(principal.roles) if is_user else [],
            credential_id=credential_record.id,
            read_only=credential_record.read_only,
        )
