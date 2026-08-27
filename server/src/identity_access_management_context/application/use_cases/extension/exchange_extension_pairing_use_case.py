import logging
from datetime import timedelta

from identity_access_management_context.application.commands import ExchangeExtensionPairingCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionPairingRepository,
    ExtensionTokenRepository,
    SsoUserRepository,
    UserPasswordRepository,
)
from identity_access_management_context.application.responses import (
    ExchangedExtensionTokenResponse,
    PendingExtensionPairingResponse,
)
from identity_access_management_context.domain.entities import ExtensionToken
from identity_access_management_context.domain.events import ExtensionPairedEvent
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingAlreadyResolvedError,
    ExtensionPairingNotApprovedError,
    ExtensionPairingNotFoundError,
    InvalidPkceVerifierError,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import (
    ExtensionTokenSecret,
    PairingUserCode,
    PkceVerifier,
)
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class ExchangeExtensionPairingUseCase(TracedUseCase):
    """Redeem an approved pairing for a read-only bearer credential.

    Anonymous, but not unauthenticated in any meaningful sense: the PKCE
    verifier proves the caller is the device that started this pairing. That is
    what makes it safe to tell an unapproved-but-valid caller "still pending"
    instead of a uniform error, since the distinction is never disclosed to
    anyone who cannot already prove ownership.

    The token is minted here rather than at approval time, so its plaintext
    exists only in this response and in the extension's storage. Only the
    SHA-256 reaches the database.
    """

    def __init__(
        self,
        extension_pairing_repository: ExtensionPairingRepository,
        extension_token_repository: ExtensionTokenRepository,
        user_password_repository: UserPasswordRepository,
        sso_user_repository: SsoUserRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
        token_lifetime_seconds: int,
        poll_interval_seconds: int,
    ):
        self._extension_pairing_repository = extension_pairing_repository
        self._extension_token_repository = extension_token_repository
        self._user_password_repository = user_password_repository
        self._sso_user_repository = sso_user_repository
        self._event_publisher = event_publisher
        self._admin_event_repository = admin_event_repository
        self._time_provider = time_provider
        self._token_lifetime_seconds = token_lifetime_seconds
        self._poll_interval_seconds = poll_interval_seconds

    def execute(
        self, command: ExchangeExtensionPairingCommand
    ) -> ExchangedExtensionTokenResponse | PendingExtensionPairingResponse:
        try:
            user_code = PairingUserCode.parse(command.user_code)
            verifier = PkceVerifier(value=command.code_verifier)
        except Exception as error:
            # A malformed code or verifier is indistinguishable from a wrong
            # one, so neither can be used to probe which pairings exist.
            raise ExtensionPairingNotFoundError() from error

        pairing = self._extension_pairing_repository.get_by_user_code(user_code)
        if pairing is None:
            raise ExtensionPairingNotFoundError()

        now = self._time_provider.get_current_time()

        try:
            # Checks the verifier FIRST, then expiry, denial and approval, so
            # every subsequent signal is only revealed to a proven owner.
            approver_id = pairing.ensure_exchangeable(verifier, now)
        except ExtensionPairingNotApprovedError:
            # Reachable only with a matching verifier, hence safe to disclose.
            return PendingExtensionPairingResponse(
                expires_at=pairing.expires_at,
                poll_interval_seconds=self._poll_interval_seconds,
            )
        except InvalidPkceVerifierError:
            logger.warning(
                "Extension pairing exchange rejected: verifier mismatch",
                extra={"pairing_id": str(pairing.id)},
            )
            raise

        email, display_name = self._resolve_identity(approver_id)

        # Single conditional write. Two concurrent exchanges both reach here,
        # only one gets True, so one approval yields exactly one credential.
        if not self._extension_pairing_repository.consume(pairing.id, now):
            raise ExtensionPairingAlreadyResolvedError()

        secret = ExtensionTokenSecret.generate()
        token = ExtensionToken.create(
            user_id=approver_id,
            secret=secret,
            device_name=pairing.device_name,
            lifetime=timedelta(seconds=self._token_lifetime_seconds),
            now=now,
            created_from_ip=pairing.created_from_ip,
        )
        stored = self._extension_token_repository.add(token)

        event = ExtensionPairedEvent(
            user_id=approver_id,
            token_id=stored.id,
            device_name=stored.device_name,
            created_from_ip=stored.created_from_ip,
        )
        self._event_publisher.publish(event)
        self._admin_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=approver_id,
            event_data={
                "token_id": str(stored.id),
                "device_name": stored.device_name,
                "created_from_ip": stored.created_from_ip,
            },
        )

        logger.info(
            "Extension paired",
            extra={"token_id": str(stored.id), "user_id": str(approver_id)},
        )

        return ExchangedExtensionTokenResponse(
            token=secret.value,
            token_id=stored.id,
            expires_at=stored.expires_at,
            user_id=approver_id,
            email=email,
            display_name=display_name,
        )

    def _resolve_identity(self, user_id) -> tuple[str, str]:
        # Password users and SSO users live in different tables; mirrors how
        # ValidateUserTokenUseCase resolves an identity.
        user_password = self._user_password_repository.get_by_id(user_id)
        if user_password:
            return user_password.email, user_password.display_name

        sso_user = self._sso_user_repository.get_by_user_id(user_id)
        if not sso_user:
            raise UserNotFoundException(user_id)
        return sso_user.email, sso_user.display_name
