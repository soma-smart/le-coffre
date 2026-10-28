import logging
from datetime import timedelta
from uuid import UUID

from identity_access_management_context.application.commands import ExchangeExtensionPairingCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionPairingRepository,
    TokenCredentialRecordRepository,
    UserRepository,
)
from identity_access_management_context.application.responses import (
    ExchangedExtensionTokenResponse,
    PendingExtensionPairingResponse,
)
from identity_access_management_context.application.services import (
    ExtensionAuditService,
    ExtensionPairingLookupService,
)
from identity_access_management_context.domain.entities import MAX_ACTIVE_TOKENS_PER_USER, TokenCredentialRecord
from identity_access_management_context.domain.events import ExtensionPairedEvent
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingAlreadyResolvedError,
    ExtensionPairingApprovalWithdrawnError,
    ExtensionPairingNotApprovedError,
    ExtensionPairingNotFoundError,
    InvalidPkceVerifierError,
    TooManyActiveExtensionTokensError,
    UserNotFoundException,
)
from identity_access_management_context.domain.value_objects import PkceVerifier, TokenCredential
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

    Minting here is also the only place the device cap can be enforced: the
    approval-time check is early feedback, not a bound.
    """

    def __init__(
        self,
        extension_pairing_repository: ExtensionPairingRepository,
        token_credential_record_repository: TokenCredentialRecordRepository,
        user_repository: UserRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
        token_lifetime_seconds: int,
        token_inactivity_seconds: int,
        poll_interval_seconds: int,
        max_active_tokens: int = MAX_ACTIVE_TOKENS_PER_USER,
    ):
        self.extension_pairing_repository = extension_pairing_repository
        self.token_credential_record_repository = token_credential_record_repository
        self.user_repository = user_repository
        self.event_publisher = event_publisher
        self.admin_event_repository = admin_event_repository
        self.time_provider = time_provider
        self.token_lifetime_seconds = token_lifetime_seconds
        self.token_inactivity_seconds = token_inactivity_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_active_tokens = max_active_tokens

    def execute(
        self, command: ExchangeExtensionPairingCommand
    ) -> ExchangedExtensionTokenResponse | PendingExtensionPairingResponse:
        pairing = ExtensionPairingLookupService.get_or_raise(self.extension_pairing_repository, command.user_code)

        try:
            verifier = PkceVerifier(value=command.code_verifier)
        except Exception as error:
            # A malformed verifier is indistinguishable from a wrong one, so it
            # cannot be used to probe which pairings exist.
            raise ExtensionPairingNotFoundError() from error

        now = self.time_provider.get_current_time()

        try:
            # Checks the verifier FIRST, then expiry, denial and approval, so
            # every subsequent signal is only revealed to a proven owner.
            approver_id = pairing.ensure_exchangeable(verifier, now)
        except ExtensionPairingNotApprovedError:
            # Reachable only with a matching verifier, hence safe to disclose.
            return PendingExtensionPairingResponse(
                expires_at=pairing.expires_at,
                poll_interval_seconds=self.poll_interval_seconds,
            )
        except InvalidPkceVerifierError:
            logger.warning(
                "Extension pairing exchange rejected: verifier mismatch",
                extra={"pairing_id": str(pairing.id)},
            )
            raise

        # An approval is only as good as the account that gave it. Revoking
        # every issued token on a password change or a deletion leaves one
        # thing standing: a pairing approved before the event and redeemed
        # after it, which would mint a fresh credential dated after the cutoff.
        # The account row is the authority here, not the SSO row, which
        # outlives deletion.
        approver = self.user_repository.get_by_id(approver_id)
        if approver is None:
            logger.warning(
                "Extension pairing exchange refused: approver no longer exists",
                extra={"pairing_id": str(pairing.id)},
            )
            raise ExtensionPairingApprovalWithdrawnError()
        if (
            approver.session_invalid_before is not None
            and pairing.approved_at is not None
            and pairing.approved_at < approver.session_invalid_before
        ):
            logger.warning(
                "Extension pairing exchange refused: approval predates the session cutoff",
                extra={"pairing_id": str(pairing.id), "user_id": str(approver_id)},
            )
            raise ExtensionPairingApprovalWithdrawnError()

        email, display_name = self._resolve_identity(approver_id)

        # Re-checked here, and not only at approval: approval proves the user
        # was under the cap at that moment, against that pairing. Nothing stops
        # someone at four tokens from collecting any number of approvals, each
        # seeing 4 < 5, and redeeming them afterwards. This read is the friendly
        # exit that leaves the pairing intact; the insert below is the guard.
        if self.token_credential_record_repository.count_usable(approver_id, now) >= self.max_active_tokens:
            raise TooManyActiveExtensionTokensError(self.max_active_tokens)

        # Single conditional write. Two concurrent exchanges both reach here,
        # only one gets True, so one approval yields exactly one credential.
        if not self.extension_pairing_repository.consume(pairing.id, now):
            raise ExtensionPairingAlreadyResolvedError()

        token = TokenCredential.generate()
        credential_record = TokenCredentialRecord(
            principal_id=approver_id,
            token_hash=token.hash,
            # An extension reads what its user can read, and nothing more: it
            # lives in a browser profile, far from where the user logged in.
            read_only=True,
            label=pairing.device_name,
            expires_at=now + timedelta(seconds=self.token_lifetime_seconds),
            # Counted from issuance, so an exchange whose response the extension
            # lost does not leave a live credential behind forever.
            last_used_at=now,
            max_idle=timedelta(seconds=self.token_inactivity_seconds),
        )
        if not self.token_credential_record_repository.create_within_limit(
            credential_record, self.max_active_tokens, now
        ):
            # Only reachable when a concurrent exchange took the last slot
            # between the count above and this insert. The pairing is already
            # consumed, so this one has to be re-paired after freeing a slot.
            logger.warning(
                "Extension pairing exchange refused: device cap reached",
                extra={"user_id": str(approver_id)},
            )
            raise TooManyActiveExtensionTokensError(self.max_active_tokens)

        # The token is committed: an audit or notification failure past this
        # point must not cost the user the only copy of its plaintext.
        event = ExtensionPairedEvent(
            user_id=approver_id,
            token_id=credential_record.id,
            device_name=pairing.device_name,
            created_from_ip=pairing.created_from_ip,
        )
        ExtensionAuditService.record(
            self.event_publisher,
            self.admin_event_repository,
            event,
            actor_user_id=approver_id,
            event_data={
                "token_id": str(credential_record.id),
                "device_name": pairing.device_name,
                "created_from_ip": pairing.created_from_ip,
            },
        )

        logger.info("Extension paired", extra={"token_id": str(credential_record.id), "user_id": str(approver_id)})

        return ExchangedExtensionTokenResponse(
            token=token.value,
            token_id=credential_record.id,
            expires_at=credential_record.expires_at,
            user_id=approver_id,
            email=email,
            display_name=display_name,
        )

    def _resolve_identity(self, user_id: UUID) -> tuple[str, str]:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundException(user_id)
        return user.email, user.name
