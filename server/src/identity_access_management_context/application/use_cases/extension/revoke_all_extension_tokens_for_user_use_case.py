from identity_access_management_context.application.commands import RevokeAllExtensionTokensForUserCommand
from identity_access_management_context.application.gateways import (
    AdminEventRepository,
    TokenCredentialRecordRepository,
    UserRepository,
)
from identity_access_management_context.application.services import (
    REVOCATION_REASON_ADMIN_REVOKED,
    ExtensionRevocationRecordingService,
)
from shared_kernel.application.gateways import DomainEventPublisher
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

    Only a user's tokens: a service account's id gets the same 0 as an unknown
    one. Deleting its token would leave the account active without one, and
    write an extension revocation for something that is not a user.
    """

    def __init__(
        self,
        token_credential_record_repository: TokenCredentialRecordRepository,
        user_repository: UserRepository,
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
    ):
        self.token_credential_record_repository = token_credential_record_repository
        self.user_repository = user_repository
        self.event_publisher = event_publisher
        self.admin_event_repository = admin_event_repository

    def execute(self, command: RevokeAllExtensionTokensForUserCommand) -> int:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "revoke a user's browser extensions")

        if self.user_repository.get_by_id(command.target_user_id) is None:
            return 0

        revoked = self.token_credential_record_repository.delete_by_principal_ids([command.target_user_id])

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
