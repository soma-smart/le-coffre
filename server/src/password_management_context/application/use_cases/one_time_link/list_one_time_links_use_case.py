from password_management_context.application.commands import ListOneTimeLinksCommand
from password_management_context.application.gateways import OneTimeLinkRepository
from password_management_context.application.responses import (
    ListOneTimeLinksResponse,
    OneTimeLinkSummaryResponse,
)
from password_management_context.application.services import PasswordOwnershipService
from password_management_context.domain.entities.one_time_link import (
    MAX_ACTIVE_LINKS_PER_PASSWORD,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

# Read and revoked links are kept forever for the audit trail, so the list of a
# long-lived password only ever grows. The management view needs the handful of
# recent ones; the full history of reads lives in the password event log.
MAX_LISTED_LINKS = 10


class ListOneTimeLinksUseCase(TracedUseCase):
    """List a password's one-time links, for its owner.

    Returns only the still-redeemable links by default: those are the ones the
    owner can act on, and their number is bounded by the active-link cap. Spent
    and revoked links are history, returned only on request and capped, since
    they are never deleted and would otherwise grow without end.
    """

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        ownership_service: PasswordOwnershipService,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.ownership_service = ownership_service
        self.time_gateway = time_gateway

    def execute(self, command: ListOneTimeLinksCommand) -> ListOneTimeLinksResponse:
        self.ownership_service.ensure_user_owns_password(command.requesting_user_id, command.password_id)

        now = self.time_gateway.get_current_time()

        if command.include_inactive:
            links = self.one_time_link_repository.list_for_password(command.password_id, limit=MAX_LISTED_LINKS)
        else:
            links = self.one_time_link_repository.list_active_for_password(
                command.password_id, now, limit=MAX_LISTED_LINKS
            )

        total = self.one_time_link_repository.count_for_password(command.password_id)
        active = self.one_time_link_repository.count_active_for_password(command.password_id, now)

        return ListOneTimeLinksResponse(
            links=[
                OneTimeLinkSummaryResponse(
                    id=link.id,
                    password_id=link.password_id,
                    created_by_user_id=link.created_by_user_id,
                    created_at=link.created_at,
                    expires_at=link.expires_at,
                    read_at=link.read_at,
                    revoked_at=link.revoked_at,
                )
                for link in links
            ],
            total=total,
            active=active,
            max_active=MAX_ACTIVE_LINKS_PER_PASSWORD,
        )
