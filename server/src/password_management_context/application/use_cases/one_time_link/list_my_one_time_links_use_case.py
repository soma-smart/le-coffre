from password_management_context.application.commands import ListMyOneTimeLinksCommand
from password_management_context.application.gateways import OneTimeLinkRepository
from password_management_context.application.responses import ListOneTimeLinkAuditResponse
from password_management_context.application.services import OneTimeLinkAuditAssembler
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

from .list_one_time_links_for_admin_use_case import MAX_AUDITED_LINKS


class ListMyOneTimeLinksUseCase(TracedUseCase):
    """The links the calling user issued, wherever they point.

    No permission check beyond authentication: the filter is the caller's own id,
    so there is nothing here they did not create themselves. Issuer emails are
    not resolved, since there is only one issuer and it is them.
    """

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        audit_assembler: OneTimeLinkAuditAssembler,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.audit_assembler = audit_assembler
        self.time_gateway = time_gateway

    def execute(self, command: ListMyOneTimeLinksCommand) -> ListOneTimeLinkAuditResponse:
        now = self.time_gateway.get_current_time()
        links = self.one_time_link_repository.list_for_creator(
            command.requesting_user_id, now, command.include_inactive, limit=MAX_AUDITED_LINKS
        )
        total = self.one_time_link_repository.count_for_creator(
            command.requesting_user_id, now, command.include_inactive
        )

        return ListOneTimeLinkAuditResponse(
            links=self.audit_assembler.assemble(links, with_emails=False),
            total=total,
        )
