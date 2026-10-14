import logging

from identity_access_management_context.application.commands import ApproveExtensionPairingCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionPairingRepository,
    ExtensionTokenRepository,
)
from identity_access_management_context.application.services import (
    ExtensionAuditService,
    ExtensionPairingLookupService,
)
from identity_access_management_context.domain.entities import MAX_ACTIVE_TOKENS_PER_USER
from identity_access_management_context.domain.events import ExtensionPairingApprovedEvent
from identity_access_management_context.domain.exceptions import (
    ExtensionPairingAlreadyResolvedError,
    TooManyActiveExtensionTokensError,
)
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
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
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
        max_active_tokens: int = MAX_ACTIVE_TOKENS_PER_USER,
    ):
        self.extension_pairing_repository = extension_pairing_repository
        self.extension_token_repository = extension_token_repository
        self.event_publisher = event_publisher
        self.admin_event_repository = admin_event_repository
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

        # The entity check gives the precise refusal (expired, already
        # resolved) on the copy just read. The repository call is the one that
        # counts: it succeeds only if the row is still pending at write time,
        # so a denial or a redemption that landed in between is never erased.
        pairing.approve(user_id, now)
        if not self.extension_pairing_repository.approve(pairing.id, user_id, now):
            raise ExtensionPairingAlreadyResolvedError()

        ExtensionAuditService.record(
            self.event_publisher,
            self.admin_event_repository,
            ExtensionPairingApprovedEvent(
                user_id=user_id,
                pairing_id=pairing.id,
                device_name=pairing.device_name,
                created_from_ip=pairing.created_from_ip,
            ),
            actor_user_id=user_id,
            event_data={
                "pairing_id": str(pairing.id),
                "device_name": pairing.device_name,
                "created_from_ip": pairing.created_from_ip,
            },
        )

        logger.info(
            "Extension pairing approved",
            extra={"pairing_id": str(pairing.id), "user_id": str(user_id)},
        )
