import logging

from password_management_context.application.commands import CreateOneTimeLinkCommand
from password_management_context.application.gateways import (
    OneTimeLinkRepository,
    PasswordEventRepository,
)
from password_management_context.application.responses import CreatedOneTimeLinkResponse
from password_management_context.application.services import (
    PasswordEventStorageService,
    PasswordOwnershipService,
)
from password_management_context.domain.entities import OneTimeLink
from password_management_context.domain.entities.one_time_link import (
    MAX_ACTIVE_LINKS_PER_PASSWORD,
)
from password_management_context.domain.events import OneTimeLinkCreatedEvent
from password_management_context.domain.exceptions import TooManyActiveOneTimeLinksError
from password_management_context.domain.value_objects import (
    OneTimeLinkLifetime,
    OneTimeLinkToken,
)
from shared_kernel.application.gateways import TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)


class CreateOneTimeLinkUseCase(TracedUseCase):
    """Issue a single-use, time-limited link for a password.

    Only an owner of the password may do this: the link removes authentication
    from the read path, so handing that power out is an owner-level decision.
    """

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        ownership_service: PasswordOwnershipService,
        password_event_repository: PasswordEventRepository,
        time_gateway: TimeGateway,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.ownership_service = ownership_service
        self.password_event_repository = password_event_repository
        self.time_gateway = time_gateway

    def execute(self, command: CreateOneTimeLinkCommand) -> CreatedOneTimeLinkResponse:
        self.ownership_service.ensure_user_owns_password(command.requesting_user_id, command.password_id)

        lifetime = (
            OneTimeLinkLifetime.default()
            if command.lifetime_seconds is None
            else OneTimeLinkLifetime(seconds=command.lifetime_seconds)
        )

        now = self.time_gateway.get_current_time()

        # Checked against active links only: read, revoked and expired ones have
        # released their slot, so an owner who keeps sharing over time is never
        # blocked. Only genuinely outstanding grants count against the cap.
        active_count = self.one_time_link_repository.count_active_for_password(command.password_id, now)
        if active_count >= MAX_ACTIVE_LINKS_PER_PASSWORD:
            raise TooManyActiveOneTimeLinksError(active_count, MAX_ACTIVE_LINKS_PER_PASSWORD)

        token = OneTimeLinkToken.generate()
        link = OneTimeLink.create(
            password_id=command.password_id,
            created_by_user_id=command.requesting_user_id,
            token=token,
            lifetime=lifetime,
            now=now,
        )
        self.one_time_link_repository.add(link)

        logger.info(
            "One-time link created",
            extra={
                "password_id": str(command.password_id),
                "link_id": str(link.id),
                "by_user_id": str(command.requesting_user_id),
            },
        )

        event = OneTimeLinkCreatedEvent(
            password_id=command.password_id,
            link_id=link.id,
            expires_at=link.expires_at.isoformat(),
            created_by_user_id=command.requesting_user_id,
        )
        PasswordEventStorageService(self.password_event_repository).store_event(event)

        # The raw token is returned here and nowhere else: only its hash is stored.
        return CreatedOneTimeLinkResponse(id=link.id, token=token.value, expires_at=link.expires_at)
