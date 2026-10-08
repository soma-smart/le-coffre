import logging

from identity_access_management_context.application.commands import DenyExtensionPairingCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionPairingRepository,
)
from identity_access_management_context.application.services import (
    ExtensionAuditService,
    ExtensionPairingLookupService,
)
from identity_access_management_context.domain.events import ExtensionPairingDeniedEvent
from identity_access_management_context.domain.exceptions import ExtensionPairingAlreadyResolvedError
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
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
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
    ):
        self.extension_pairing_repository = extension_pairing_repository
        self.event_publisher = event_publisher
        self.admin_event_repository = admin_event_repository
        self.time_provider = time_provider

    def execute(self, command: DenyExtensionPairingCommand) -> None:
        pairing = ExtensionPairingLookupService.get_or_raise(self.extension_pairing_repository, command.user_code)
        now = self.time_provider.get_current_time()

        # See ApproveExtensionPairingUseCase: the entity check explains, the
        # conditional write decides. A denial that loses to a concurrent
        # approval must say so rather than report success.
        pairing.deny(now)
        if not self.extension_pairing_repository.deny(pairing.id, now):
            raise ExtensionPairingAlreadyResolvedError()

        user_id = command.requesting_user.user_id
        ExtensionAuditService.record(
            self.event_publisher,
            self.admin_event_repository,
            ExtensionPairingDeniedEvent(
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
            "Extension pairing denied",
            extra={"pairing_id": str(pairing.id), "user_id": str(command.requesting_user.user_id)},
        )
