from identity_access_management_context.application.commands import GetExtensionPairingCommand
from identity_access_management_context.application.gateways import ExtensionPairingRepository
from identity_access_management_context.application.responses import ExtensionPairingDetailsResponse
from identity_access_management_context.application.services import ExtensionPairingLookupService
from identity_access_management_context.domain.exceptions import ExtensionPairingNotFoundError
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


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
        token_lifetime_seconds: int,
    ):
        self.extension_pairing_repository = extension_pairing_repository
        self.time_provider = time_provider
        self.token_lifetime_seconds = token_lifetime_seconds

    def execute(self, command: GetExtensionPairingCommand) -> ExtensionPairingDetailsResponse:
        pairing = ExtensionPairingLookupService.get_or_raise(self.extension_pairing_repository, command.user_code)
        now = self.time_provider.get_current_time()

        if pairing.is_expired(now):
            raise ExtensionPairingNotFoundError()

        return ExtensionPairingDetailsResponse(
            user_code=pairing.user_code.value,
            device_name=pairing.device_name,
            created_at=pairing.created_at,
            expires_at=pairing.expires_at,
            access_lifetime_seconds=self.token_lifetime_seconds,
            created_from_ip=pairing.created_from_ip,
            is_resolved=pairing.is_resolved(),
        )
