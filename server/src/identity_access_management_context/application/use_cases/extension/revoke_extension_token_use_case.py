from identity_access_management_context.application.commands import RevokeExtensionTokenCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionTokenRepository,
)
from identity_access_management_context.application.services import (
    REVOCATION_REASON_USER_REQUEST,
    ExtensionRevocationRecordingService,
)
from identity_access_management_context.domain.exceptions import ExtensionTokenNotFoundError
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class RevokeExtensionTokenUseCase(TracedUseCase):
    """Disconnect one device."""

    def __init__(
        self,
        extension_token_repository: ExtensionTokenRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        time_provider: TimeGateway,
    ):
        self.extension_token_repository = extension_token_repository
        self.event_publisher = event_publisher
        self.admin_event_repository = admin_event_repository
        self.time_provider = time_provider

    def execute(self, command: RevokeExtensionTokenCommand) -> None:
        token = self.extension_token_repository.get_by_id(command.token_id)

        # Someone else's token is reported as missing rather than forbidden, so
        # this route cannot be used to discover which token ids exist.
        if token is None or token.user_id != command.requesting_user.user_id:
            raise ExtensionTokenNotFoundError()

        now = self.time_provider.get_current_time()
        if not self.extension_token_repository.revoke(token.id, now):
            # Already revoked. Idempotent from the caller's point of view: the
            # device is disconnected either way, and re-recording would put a
            # second, misleading entry in the audit trail.
            return

        ExtensionRevocationRecordingService.record(
            self.event_publisher,
            self.admin_event_repository,
            user_id=command.requesting_user.user_id,
            token_id=token.id,
            reason=REVOCATION_REASON_USER_REQUEST,
            revoked_count=1,
        )
