import logging

from password_management_context.application.commands import RevokeAllOneTimeLinksForUserCommand
from password_management_context.application.gateways import OneTimeLinkRepository
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase
from shared_kernel.domain.services import AdminPermissionChecker

logger = logging.getLogger(__name__)


class RevokeAllOneTimeLinksForUserUseCase(TracedUseCase):
    """Cut every live link one user issued, in one go.

    The case this exists for: someone is leaving, and the links they handed out
    would otherwise outlive their account. Returns how many were actually cut, so
    the caller can say "3 links revoked" rather than guess.
    """

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.time_gateway = time_gateway

    def execute(self, command: RevokeAllOneTimeLinksForUserCommand) -> int:
        AdminPermissionChecker.ensure_admin(command.requesting_user, "revoke a user's one-time links")

        now = self.time_gateway.get_current_time()
        revoked = self.one_time_link_repository.revoke_all_for_creator(command.target_user_id, now)

        logger.info(
            "One-time links revoked in bulk",
            extra={
                "target_user_id": str(command.target_user_id),
                "revoked_count": revoked,
                "by_user_id": str(command.requesting_user.user_id),
            },
        )
        return revoked
