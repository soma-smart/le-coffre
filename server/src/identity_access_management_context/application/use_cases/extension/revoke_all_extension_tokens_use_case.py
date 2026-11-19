from identity_access_management_context.application.commands import RevokeAllExtensionTokensCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    TokenCredentialRecordRepository,
)
from identity_access_management_context.application.services import (
    REVOCATION_REASON_USER_REQUEST,
    ExtensionRevocationRecordingService,
)
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.application.tracing import TracedUseCase


class RevokeAllExtensionTokensUseCase(TracedUseCase):
    """Disconnect every device at once."""

    def __init__(
        self,
        token_credential_record_repository: TokenCredentialRecordRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
    ):
        self.token_credential_record_repository = token_credential_record_repository
        self.event_publisher = event_publisher
        self.admin_event_repository = admin_event_repository

    def execute(self, command: RevokeAllExtensionTokensCommand) -> int:
        user_id = command.requesting_user.user_id
        revoked = self.token_credential_record_repository.delete_by_principal_ids([user_id])

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
