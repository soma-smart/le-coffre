import logging
from uuid import UUID

from identity_access_management_context.application.commands import ValidateExtensionTokenCommand
from identity_access_management_context.application.gateways import (
    ExtensionTokenRepository,
    SsoUserRepository,
    UserPasswordRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import ValidatedExtensionTokenResponse
from identity_access_management_context.domain.exceptions import (
    ExtensionTokenNotFoundError,
    ExtensionTokenRevokedError,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import ExtensionTokenSecret
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
        extension_token_repository: ExtensionTokenRepository,
        user_password_repository: UserPasswordRepository,
        sso_user_repository: SsoUserRepository,
        user_repository: UserRepository,
        time_provider: TimeGateway,
        last_used_coarsening_seconds: int,
    ):
        self.extension_token_repository = extension_token_repository
        self.user_password_repository = user_password_repository
        self.sso_user_repository = sso_user_repository
        self.user_repository = user_repository
        self.time_provider = time_provider
        self.last_used_coarsening_seconds = last_used_coarsening_seconds

    def execute(self, command: ValidateExtensionTokenCommand) -> ValidatedExtensionTokenResponse:
        try:
            secret = ExtensionTokenSecret(value=command.raw_token)
        except Exception as error:
            # Too short to have come from generate(), so it never reaches a
            # database lookup.
            raise ExtensionTokenNotFoundError() from error

        token = self.extension_token_repository.get_by_token_hash(secret.hashed())
        if token is None:
            raise ExtensionTokenNotFoundError()

        now = self.time_provider.get_current_time()
        # Raises ExtensionTokenRevokedError / ExtensionTokenExpiredError.
        token.ensure_usable(now)

        authenticated_user = self.user_repository.get_by_id(token.user_id)
        if authenticated_user is not None and authenticated_user.session_invalid_before is not None:
            # The same cutoff that kills cookie sessions on a password change or
            # on refresh-token reuse detection. Without honouring it here,
            # "change my password to log everything out" would silently leave
            # every paired extension alive.
            if token.created_at < authenticated_user.session_invalid_before:
                raise ExtensionTokenRevokedError()

        email, display_name = self._resolve_identity(token.user_id)

        # Best-effort telemetry for the connected-devices screen. It must never
        # fail authentication, so a storage hiccup here is swallowed.
        try:
            self.extension_token_repository.touch_last_used(token.id, now, self.last_used_coarsening_seconds)
        except Exception:  # noqa: BLE001 - telemetry must not break auth
            logger.warning("Could not record extension token usage", exc_info=True)

        return ValidatedExtensionTokenResponse(
            user_id=token.user_id,
            email=email,
            display_name=display_name,
            token_id=token.id,
        )

    def _resolve_identity(self, user_id: UUID) -> tuple[str, str]:
        user_password = self.user_password_repository.get_by_id(user_id)
        if user_password:
            return user_password.email, user_password.display_name

        sso_user = self.sso_user_repository.get_by_user_id(user_id)
        if not sso_user:
            raise UserNotFoundException(user_id)
        return sso_user.email, sso_user.display_name
