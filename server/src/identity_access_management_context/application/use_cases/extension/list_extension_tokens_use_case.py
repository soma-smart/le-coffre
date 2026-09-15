from identity_access_management_context.application.commands import ListExtensionTokensCommand
from identity_access_management_context.application.gateways import ExtensionTokenRepository
from identity_access_management_context.application.responses import (
    ExtensionTokenSummary,
    ListExtensionTokensResponse,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase


class ListExtensionTokensUseCase(TracedUseCase):
    """The connected-devices screen.

    Returns revoked and expired entries too: a user checking "did I actually
    disconnect that laptop" needs to see the answer, not an empty row.
    """

    def __init__(
        self,
        extension_token_repository: ExtensionTokenRepository,
        time_provider: TimeGateway,
    ):
        self.extension_token_repository = extension_token_repository
        self.time_provider = time_provider

    def execute(self, command: ListExtensionTokensCommand) -> ListExtensionTokensResponse:
        now = self.time_provider.get_current_time()
        tokens = self.extension_token_repository.list_for_user(command.requesting_user.user_id)

        return ListExtensionTokensResponse(
            tokens=[
                ExtensionTokenSummary(
                    id=token.id,
                    device_name=token.device_name,
                    created_at=token.created_at,
                    expires_at=token.expires_at,
                    last_used_at=token.last_used_at,
                    revoked_at=token.revoked_at,
                    created_from_ip=token.created_from_ip,
                    is_active=token.is_active(now),
                )
                for token in tokens
            ]
        )
