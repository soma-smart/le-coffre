from identity_access_management_context.application.commands import ListExtensionTokensCommand
from identity_access_management_context.application.gateways import TokenCredentialRecordRepository
from identity_access_management_context.application.responses import (
    ExtensionTokenSummary,
    ListExtensionTokensResponse,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class ListExtensionTokensUseCase(TracedUseCase):
    """The connected-devices screen.

    Expired and idle tokens are listed as inactive, until revoked. A revoked
    token is gone: its history lives in the audit trail.
    """

    def __init__(
        self,
        token_credential_record_repository: TokenCredentialRecordRepository,
        time_provider: TimeGateway,
    ):
        self.token_credential_record_repository = token_credential_record_repository
        self.time_provider = time_provider

    def execute(self, command: ListExtensionTokensCommand) -> ListExtensionTokensResponse:
        now = self.time_provider.get_current_time()
        tokens = self.token_credential_record_repository.list_by_principal_ids((command.requesting_user.user_id,))

        return ListExtensionTokensResponse(
            tokens=[
                ExtensionTokenSummary(
                    id=token.id,
                    device_name=token.label,
                    expires_at=token.expires_at,
                    last_used_at=token.last_used_at,
                    # The same notion of active that authentication applies, so
                    # a token refused for inactivity is not listed as live.
                    is_active=token.is_usable(now),
                )
                for token in tokens
            ]
        )
