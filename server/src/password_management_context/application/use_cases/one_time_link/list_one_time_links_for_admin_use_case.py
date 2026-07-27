from password_management_context.application.commands import ListOneTimeLinksForAdminCommand
from password_management_context.application.gateways import OneTimeLinkRepository
from password_management_context.application.responses import ListOneTimeLinkAuditResponse
from password_management_context.application.services import OneTimeLinkAuditAssembler
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker

# Generous, because the point of this table is to see the whole picture, and the
# UI paginates client-side. Still bounded: spent links are never deleted, so an
# unbounded query would grow with the vault's entire history.
MAX_AUDITED_LINKS = 200


class ListOneTimeLinksForAdminUseCase(TracedUseCase):
    """Every one-time link in the vault, for an administrator."""

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        audit_assembler: OneTimeLinkAuditAssembler,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.audit_assembler = audit_assembler
        self.time_gateway = time_gateway

    def execute(self, command: ListOneTimeLinksForAdminCommand) -> ListOneTimeLinkAuditResponse:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "list one-time links")

        now = self.time_gateway.get_current_time()
        links = self.one_time_link_repository.list_all(now, command.include_inactive, limit=MAX_AUDITED_LINKS)
        total = self.one_time_link_repository.count_all_matching(now, command.include_inactive)

        return ListOneTimeLinkAuditResponse(
            links=self.audit_assembler.assemble(links, with_issuers=True),
            total=total,
        )
