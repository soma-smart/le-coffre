import logging

from identity_access_management_context.application.commands import (
    ApproveExtensionPairingCommand,
    DenyExtensionPairingCommand,
    GetExtensionPairingCommand,
)
from identity_access_management_context.application.gateways import (
    ExtensionPairingRepository,
    ExtensionTokenRepository,
)
from identity_access_management_context.application.responses import ExtensionPairingDetailsResponse
from identity_access_management_context.domain.entities import MAX_ACTIVE_TOKENS_PER_USER
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingNotFoundError,
    TooManyActiveExtensionTokensError,
)
from identity_access_management_context.domain.value_objects import PairingUserCode
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class GetExtensionPairingUseCase(TracedUseCase):
    """Back the approval page with server-vouched facts about a pairing.

    Requires a session, so a pairing cannot be inspected by whoever merely knows
    the code. What it returns is deliberately thin: enough for the user to
    decide, nothing that would help someone who guessed a code.
    """

    def __init__(
        self,
        extension_pairing_repository: ExtensionPairingRepository,
        time_provider: TimeGateway,
    ):
        self._extension_pairing_repository = extension_pairing_repository
        self._time_provider = time_provider

    def execute(self, command: GetExtensionPairingCommand) -> ExtensionPairingDetailsResponse:
        pairing = _load_pairing(self._extension_pairing_repository, command.user_code)
        now = self._time_provider.get_current_time()

        if pairing.is_expired(now):
            raise ExtensionPairingNotFoundError()

        return ExtensionPairingDetailsResponse(
            user_code=pairing.user_code.value,
            device_name=pairing.device_name,
            created_at=pairing.created_at,
            expires_at=pairing.expires_at,
            created_from_ip=pairing.created_from_ip,
            is_resolved=pairing.is_resolved(),
        )


class ApproveExtensionPairingUseCase(TracedUseCase):
    """Bind a pending pairing to the logged in user.

    No credential is minted here. The token is created during the exchange, so
    its plaintext never has to wait anywhere for the extension to collect it: it
    exists only in the exchange response and in the extension's own storage.
    """

    def __init__(
        self,
        extension_pairing_repository: ExtensionPairingRepository,
        extension_token_repository: ExtensionTokenRepository,
        time_provider: TimeGateway,
        max_active_tokens: int = MAX_ACTIVE_TOKENS_PER_USER,
    ):
        self._extension_pairing_repository = extension_pairing_repository
        self._extension_token_repository = extension_token_repository
        self._time_provider = time_provider
        self._max_active_tokens = max_active_tokens

    def execute(self, command: ApproveExtensionPairingCommand) -> None:
        pairing = _load_pairing(self._extension_pairing_repository, command.user_code)
        now = self._time_provider.get_current_time()
        user_id = command.requesting_user.user_id

        # Checked at approval rather than at exchange so the user is told they
        # are at the cap while they are still looking at a screen that can
        # explain it, instead of the extension failing silently a moment later.
        active = self._extension_token_repository.count_active_for_user(user_id, now)
        if active >= self._max_active_tokens:
            raise TooManyActiveExtensionTokensError(self._max_active_tokens)

        # Raises if already approved, denied, consumed or expired.
        pairing.approve(user_id, now)
        self._extension_pairing_repository.save(pairing)

        logger.info(
            "Extension pairing approved",
            extra={"pairing_id": str(pairing.id), "user_id": str(user_id)},
        )


class DenyExtensionPairingUseCase(TracedUseCase):
    """Refuse a pairing.

    Exists so a user who realises they are being phished gets an immediate,
    deliberate way out. Without it the only option is closing the tab, and the
    extension would keep polling until the request times out.
    """

    def __init__(
        self,
        extension_pairing_repository: ExtensionPairingRepository,
        time_provider: TimeGateway,
    ):
        self._extension_pairing_repository = extension_pairing_repository
        self._time_provider = time_provider

    def execute(self, command: DenyExtensionPairingCommand) -> None:
        pairing = _load_pairing(self._extension_pairing_repository, command.user_code)
        now = self._time_provider.get_current_time()

        pairing.deny(now)
        self._extension_pairing_repository.save(pairing)

        logger.info(
            "Extension pairing denied",
            extra={"pairing_id": str(pairing.id), "user_id": str(command.requesting_user.user_id)},
        )


def _load_pairing(repository: ExtensionPairingRepository, raw_user_code: str):
    # PairingUserCode.parse raises on a malformed code, which is the same
    # outcome as a code that simply does not exist. Both surface as
    # ExtensionPairingNotFoundError so a caller cannot use well-formedness as a
    # probe.
    try:
        user_code = PairingUserCode.parse(raw_user_code)
    except Exception as error:
        raise ExtensionPairingNotFoundError() from error

    pairing = repository.get_by_user_code(user_code)
    if pairing is None:
        raise ExtensionPairingNotFoundError()
    return pairing
