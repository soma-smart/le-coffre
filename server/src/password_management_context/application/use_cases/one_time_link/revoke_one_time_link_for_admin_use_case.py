import logging

from password_management_context.application.commands import RevokeOneTimeLinkForAdminCommand
from password_management_context.application.gateways import OneTimeLinkRepository
from password_management_context.domain.exceptions import OneTimeLinkNotFoundError
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker

logger = logging.getLogger(__name__)


class RevokeOneTimeLinkForAdminUseCase(TracedUseCase):
    """Kill any unread link in the vault, regardless of who issued it.

    Separate from the owner-facing use case rather than a flag on it: the two
    answer to different authorities, and folding them together would put an
    admin bypass inside the path every owner takes.
    """

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.time_gateway = time_gateway

    def execute(self, command: RevokeOneTimeLinkForAdminCommand) -> None:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "revoke a one-time link")

        link = self.one_time_link_repository.get_by_id(command.link_id)
        if link is None:
            raise OneTimeLinkNotFoundError()

        now = self.time_gateway.get_current_time()
        if not self.one_time_link_repository.revoke(command.link_id, now):
            # Already read or revoked: nothing to kill, and the read timestamp
            # must survive as audit data.
            raise OneTimeLinkNotFoundError()

        logger.info(
            "One-time link revoked by admin",
            extra={
                "link_id": str(link.id),
                "password_id": str(link.password_id),
                "issued_by_user_id": str(link.created_by_user_id),
                "by_user_id": str(command.requesting_user.user_id),
            },
        )
