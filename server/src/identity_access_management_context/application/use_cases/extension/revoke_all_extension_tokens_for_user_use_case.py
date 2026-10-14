from identity_access_management_context.application.commands import RevokeAllExtensionTokensForUserCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    ExtensionTokenRepository,
)
from identity_access_management_context.application.services import (
    REVOCATION_REASON_ADMIN_REVOKED,
    ExtensionRevocationRecordingService,
)
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker


class RevokeAllExtensionTokensForUserUseCase(TracedUseCase):
    """Disconnect every browser extension of another account, as an administrator.

    The case this exists for: someone is disabled in the identity provider but
    not yet removed from the vault, or a laptop is reported stolen and its
    owner is unreachable. Until now only the owner could cut their own
    extensions, so an administrator's only lever was deleting the account.
    Returns how many were actually cut, so the caller can say so rather than
    guess.
    """

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

    def execute(self, command: RevokeAllExtensionTokensForUserCommand) -> int:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "revoke a user's browser extensions")

        now = self.time_provider.get_current_time()
        revoked = self.extension_token_repository.revoke_all_for_user(command.target_user_id, now)

        if revoked:
            # Actor and owner differ here, which is exactly what the audit
            # trail records them apart for.
            ExtensionRevocationRecordingService.record(
                self.event_publisher,
                self.admin_event_repository,
                user_id=command.target_user_id,
                actor_user_id=command.requesting_user.user_id,
                token_id=None,
                reason=REVOCATION_REASON_ADMIN_REVOKED,
                revoked_count=revoked,
            )
        return revoked
