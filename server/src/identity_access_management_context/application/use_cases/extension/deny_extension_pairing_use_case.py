import logging

from identity_access_management_context.application.commands import DenyExtensionPairingCommand
from identity_access_management_context.application.gateways import ExtensionPairingRepository
from identity_access_management_context.application.services import ExtensionPairingLookupService
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


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
        self.extension_pairing_repository = extension_pairing_repository
        self.time_provider = time_provider

    def execute(self, command: DenyExtensionPairingCommand) -> None:
        pairing = ExtensionPairingLookupService.get_or_raise(self.extension_pairing_repository, command.user_code)
        now = self.time_provider.get_current_time()

        pairing.deny(now)
        self.extension_pairing_repository.save(pairing)

        logger.info(
            "Extension pairing denied",
            extra={"pairing_id": str(pairing.id), "user_id": str(command.requesting_user.user_id)},
        )
