from identity_access_management_context.application.commands import RevokeAllExtensionTokensCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionTokenRepository,
)
from identity_access_management_context.application.services import (
    REVOCATION_REASON_USER_REQUEST,
    ExtensionRevocationRecordingService,
)
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class RevokeAllExtensionTokensUseCase(TracedUseCase):
    """Disconnect every device at once."""

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

    def execute(self, command: RevokeAllExtensionTokensCommand) -> int:
        user_id = command.requesting_user.user_id
        now = self.time_provider.get_current_time()
        revoked = self.extension_token_repository.revoke_all_for_user(user_id, now)

        if revoked:
            ExtensionRevocationRecordingService.record(
                self.event_publisher,
                self.admin_event_repository,
                user_id=user_id,
                actor_user_id=user_id,
                token_id=None,
                reason=REVOCATION_REASON_USER_REQUEST,
                revoked_count=revoked,
            )
        return revoked
