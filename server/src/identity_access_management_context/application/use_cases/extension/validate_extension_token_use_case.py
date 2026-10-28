import logging
from datetime import timedelta
from uuid import UUID

from identity_access_management_context.application.commands import ValidateExtensionTokenCommand
from identity_access_management_context.application.gateways import (
    TokenCredentialRecordRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import ValidatedExtensionTokenResponse
from identity_access_management_context.domain.exceptions import (
    ExtensionTokenExpiredError,
    ExtensionTokenNotFoundError,
    InvalidTokenCredentialError,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import TokenCredential
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class ValidateExtensionTokenUseCase(TracedUseCase):
    """Resolve a bearer credential to an identity.

    Mirrors ValidateUserTokenUseCase: credential, then revocation, then the
    account-wide cutoff, then identity. Every failure raises an ExtensionDomain
    error carrying the same message, so the caller can log which one fired
    without letting a token holder tell revoked from expired.

    Note what is NOT returned: roles. The caller assembles a principal with a
    fixed non-admin role. Echoing the user's own roles would mean an admin's
    extension token makes `/passwords/list` return the names, logins and URLs
    of every secret on the instance, and that list would then be sitting in a
    browser profile. (It would not expose the secrets themselves: GetPassword
    has no admin bypass, access there is purely group-based.)
    """

    def __init__(
        self,
        token_credential_record_repository: TokenCredentialRecordRepository,
        user_repository: UserRepository,
        time_provider: TimeGateway,
        last_used_coarsening_seconds: int,
    ):
        self.token_credential_record_repository = token_credential_record_repository
        self.user_repository = user_repository
        self.time_provider = time_provider
        self.last_used_coarsening = timedelta(seconds=last_used_coarsening_seconds)

    def execute(self, command: ValidateExtensionTokenCommand) -> ValidatedExtensionTokenResponse:
        try:
            token = TokenCredential(value=command.raw_token)
        except InvalidTokenCredentialError as error:
            # Too short to have come from generate(), so it never reaches a
            # database lookup.
            raise ExtensionTokenNotFoundError() from error

        credential_record = self.token_credential_record_repository.get_by_token_hash(token.hash)
        if credential_record is None:
            raise ExtensionTokenNotFoundError()

        now = self.time_provider.get_current_time()
        # The absolute lifetime bounds a token in use; the inactivity limit
        # bounds one that is not, so a laptop in a drawer does not hold a live
        # grant for the rest of the month.
        if not credential_record.is_usable(now):
            raise ExtensionTokenExpiredError()

        email, display_name = self._resolve_identity(credential_record.principal_id)

        # Best-effort: it must never fail authentication, so a storage hiccup
        # here is swallowed.
        try:
            self.token_credential_record_repository.touch_last_used(
                credential_record.id, now, self.last_used_coarsening
            )
        except Exception:  # noqa: BLE001 - recording use must not break auth
            logger.warning("Could not record extension token usage", exc_info=True)

        return ValidatedExtensionTokenResponse(
            user_id=credential_record.principal_id,
            email=email,
            display_name=display_name,
            token_id=credential_record.id,
        )

    def _resolve_identity(self, user_id: UUID) -> tuple[str, str]:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException(user_id)
        return user.email, user.name
