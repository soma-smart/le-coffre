import logging

from password_management_context.application.commands import RevokeOneTimeLinkCommand
from password_management_context.application.gateways import OneTimeLinkRepository
from password_management_context.application.services import PasswordOwnershipService
from password_management_context.domain.exceptions import OneTimeLinkNotFoundError
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class RevokeOneTimeLinkUseCase(TracedUseCase):
    """Kill a link that has not been read yet."""

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        ownership_service: PasswordOwnershipService,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.ownership_service = ownership_service
        self.time_gateway = time_gateway

    def execute(self, command: RevokeOneTimeLinkCommand) -> None:
        link = self.one_time_link_repository.get_by_id(command.link_id)
        if link is None:
            raise OneTimeLinkNotFoundError()

        # Whoever issued the link may always take it back, even after losing
        # ownership of the password. That is the case this feature exists for:
        # someone leaves a team, loses the ownership that let them issue a link,
        # and must still be able to cut the grant they left behind. Revoking only
        # ever removes access, never grants it, so widening this is safe.
        if link.created_by_user_id != command.requesting_user_id:
            self.ownership_service.ensure_user_owns_password(command.requesting_user_id, link.password_id)

        now = self.time_gateway.get_current_time()
        if not self.one_time_link_repository.revoke(command.link_id, now):
            # Already read or already revoked. Nothing to kill, and we must not
            # overwrite the read timestamp that the audit trail depends on.
            raise OneTimeLinkNotFoundError()

        logger.info(
            "One-time link revoked",
            extra={
                "password_id": str(link.password_id),
                "link_id": str(link.id),
                "by_user_id": str(command.requesting_user_id),
            },
        )
