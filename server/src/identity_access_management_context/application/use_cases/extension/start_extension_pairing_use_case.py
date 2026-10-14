import logging
from datetime import timedelta

from identity_access_management_context.application.commands import StartExtensionPairingCommand
from identity_access_management_context.application.gateways import ExtensionPairingRepository
from identity_access_management_context.application.responses import StartedExtensionPairingResponse
from identity_access_management_context.domain.entities import ExtensionPairing
from identity_access_management_context.domain.value_objects import PairingUserCode, PkceChallenge
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)

# A self-reported device name is untrusted input that ends up rendered on the
# approval page. Truncating bounds what an attacker can push into that view.
MAX_DEVICE_NAME_LENGTH = 60
DEFAULT_DEVICE_NAME = "Unnamed device"


class StartExtensionPairingUseCase(TracedUseCase):
    """Register a pairing request before the extension opens the approval tab.

    Anonymous by necessity: the extension has no credential yet. It is safe
    because the row this creates grants nothing. Approving it requires a logged
    in session, and redeeming it additionally requires the PKCE verifier, which
    never leaves the extension.
    """

    def __init__(
        self,
        extension_pairing_repository: ExtensionPairingRepository,
        time_provider: TimeGateway,
        pairing_lifetime_seconds: int,
        poll_interval_seconds: int,
    ):
        self.extension_pairing_repository = extension_pairing_repository
        self.time_provider = time_provider
        self.pairing_lifetime_seconds = pairing_lifetime_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def execute(self, command: StartExtensionPairingCommand) -> StartedExtensionPairingResponse:
        # Raises UnsupportedPkceMethodError for anything but S256, so a client
        # cannot negotiate the binding away by asking for `plain`.
        challenge = PkceChallenge.parse(command.code_challenge, command.code_challenge_method)

        now = self.time_provider.get_current_time()
        # Cheap opportunistic cleanup: pairings are short-lived and only ever
        # read by user_code, so dead rows are pure noise in the table.
        self.extension_pairing_repository.purge_expired(now)

        pairing = ExtensionPairing.create(
            user_code=PairingUserCode.generate(),
            code_challenge=challenge,
            device_name=self._sanitize_device_name(command.device_name),
            lifetime=timedelta(seconds=self.pairing_lifetime_seconds),
            now=now,
            created_from_ip=command.created_from_ip,
        )
        stored = self.extension_pairing_repository.add(pairing)

        logger.info(
            "Extension pairing started",
            extra={"pairing_id": str(stored.id), "device_name": stored.device_name},
        )

        return StartedExtensionPairingResponse(
            user_code=stored.user_code.value,
            expires_at=stored.expires_at,
            poll_interval_seconds=self.poll_interval_seconds,
        )

    @staticmethod
    def _sanitize_device_name(raw: str | None) -> str:
        # Control characters would let a caller forge line breaks in the
        # approval page and in log lines.
        cleaned = "".join(character for character in (raw or "") if character.isprintable()).strip()
        return cleaned[:MAX_DEVICE_NAME_LENGTH] or DEFAULT_DEVICE_NAME
