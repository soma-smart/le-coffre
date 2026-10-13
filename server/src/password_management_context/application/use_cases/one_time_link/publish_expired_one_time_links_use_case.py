import logging

from password_management_context.application.gateways import OneTimeLinkRepository, PasswordRepository
from password_management_context.domain.events import OneTimeLinkExpiredEvent
from password_management_context.domain.exceptions import PasswordNotFoundError
from shared_kernel.application.gateways import DomainEventPublisher, TimeGateway
from shared_kernel.application.tracing import TracedUseCase

logger = logging.getLogger(__name__)

# Upper bound on the links handled per pass, so one pass never loads an unbounded
# table. A backlog larger than this is simply worked through over the next passes.
EXPIRY_SWEEP_BATCH_SIZE = 100


class PublishExpiredOneTimeLinksUseCase(TracedUseCase):
    """System use case: tell the creators whose one-time link expired unread.

    Expiry is passive (a clock comparison), so nothing happens at the moment a link
    runs out; this runs periodically and turns "expired" into an event.

    Each link is first *claimed* with one conditional write, and only the caller
    that wins the claim publishes. Same guarantee as `consume()`: with several
    replicas sweeping at once, an expiry event is published at most once per link.
    A link is claimed even when its password is gone or publishing is impossible, so
    it is never picked again.

    Known and accepted race: a link read at the very end of its life, concurrently
    with a sweep that sees it as expired, can yield both the "opened" and the
    "expired" email. The window is tiny and the emails are courtesy notices, so it
    is not worth a lock.
    """

    def __init__(
        self,
        one_time_link_repository: OneTimeLinkRepository,
        password_repository: PasswordRepository,
        event_publisher: DomainEventPublisher,
        time_gateway: TimeGateway,
        batch_size: int = EXPIRY_SWEEP_BATCH_SIZE,
    ):
        self.one_time_link_repository = one_time_link_repository
        self.password_repository = password_repository
        self.event_publisher = event_publisher
        self.time_gateway = time_gateway
        self.batch_size = batch_size

    def execute(self) -> int:
        """Publish one event per newly expired link of this batch; returns how many."""
        now = self.time_gateway.get_current_time()
        published = 0

        for link in self.one_time_link_repository.list_expired_pending_notification(now, self.batch_size):
            if not self.one_time_link_repository.claim_expiry_notification(link.id, now):
                continue  # another replica got it first

            try:
                password = self.password_repository.get_by_id(link.password_id)
            except PasswordNotFoundError:
                # Links are deleted with their password, so this only happens in the
                # window around a deletion: there is nothing left to name.
                continue

            self.event_publisher.publish(
                OneTimeLinkExpiredEvent(
                    password_id=link.password_id,
                    link_id=link.id,
                    created_by_user_id=link.created_by_user_id,
                    password_name=password.name,
                    expires_at=link.expires_at,
                )
            )
            published += 1

        if published:
            logger.info("Published %d one-time link expiry event(s)", published)
        return published
