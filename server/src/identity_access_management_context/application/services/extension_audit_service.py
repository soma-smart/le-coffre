import logging
from uuid import UUID

from identity_access_management_context.application.gateways import AdminEventRepository
from shared_kernel.application.gateways import DomainEventPublisher
from shared_kernel.domain.entities import DomainEvent

logger = logging.getLogger(__name__)


class ExtensionAuditService:
    """Publish an extension event and append it to the admin log, best-effort.

    Called after the state change it describes is committed, so a failure
    here is logged rather than raised: undoing nothing, it would only turn a
    completed action into a 500.
    """

    @staticmethod
    def record(
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        event: DomainEvent,
        actor_user_id: UUID,
        event_data: dict[str, str | None],
    ) -> None:
        try:
            event_publisher.publish(event)
            admin_event_repository.append_event(
                event_id=event.event_id,
                event_type=type(event).__name__,
                occurred_on=event.occurred_on,
                actor_user_id=actor_user_id,
                event_data=event_data,
            )
        except Exception:  # noqa: BLE001 - the audited action is already committed
            logger.exception(
                "Could not record an extension audit event",
                extra={"event_type": type(event).__name__, "actor_user_id": str(actor_user_id)},
            )
