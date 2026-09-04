import logging

from identity_access_management_context.application.commands import ApproveExtensionPairingCommand
from identity_access_management_context.application.gateways import (
    ExtensionPairingRepository,
    ExtensionTokenRepository,
)
from identity_access_management_context.application.services import ExtensionPairingLookupService
from identity_access_management_context.domain.entities import MAX_ACTIVE_TOKENS_PER_USER
from identity_access_management_context.domain.exceptions import TooManyActiveExtensionTokensError
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class ApproveExtensionPairingUseCase(TracedUseCase):
    """Bind a pending pairing to the logged in user.

    No credential is minted here. The token is created during the exchange, so
    its plaintext never has to wait anywhere for the extension to collect it: it
    exists only in the exchange response and in the extension's own storage.

    Which is also why the device cap below cannot be enforced from here.
    """

    def __init__(
        self,
        extension_pairing_repository: ExtensionPairingRepository,
        extension_token_repository: ExtensionTokenRepository,
        time_provider: TimeGateway,
        max_active_tokens: int = MAX_ACTIVE_TOKENS_PER_USER,
    ):
        self.extension_pairing_repository = extension_pairing_repository
        self.extension_token_repository = extension_token_repository
        self.time_provider = time_provider
        self.max_active_tokens = max_active_tokens

    def execute(self, command: ApproveExtensionPairingCommand) -> None:
        pairing = ExtensionPairingLookupService.get_or_raise(self.extension_pairing_repository, command.user_code)
        now = self.time_provider.get_current_time()
        user_id = command.requesting_user.user_id

        # Early feedback, not the bound: approving mints nothing, so any
        # number of approvals can pass this same check while the count sits
        # still. ExchangeExtensionPairingUseCase enforces the cap where the
        # token is created. This one exists so the user is told they are at the
        # cap while still looking at a screen that can explain it, instead of
        # the extension failing a moment later with no context.
        active = self.extension_token_repository.count_active_for_user(user_id, now)
        if active >= self.max_active_tokens:
            raise TooManyActiveExtensionTokensError(self.max_active_tokens)

        pairing.approve(user_id, now)
        self.extension_pairing_repository.save(pairing)

        logger.info(
            "Extension pairing approved",
            extra={"pairing_id": str(pairing.id), "user_id": str(user_id)},
        )
