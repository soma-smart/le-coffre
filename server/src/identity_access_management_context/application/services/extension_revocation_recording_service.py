import logging
from uuid import UUID

from identity_access_management_context.application.gateways import AdminEventRepository
from identity_access_management_context.domain.events import ExtensionTokenRevokedEvent
from shared_kernel.application.gateways import DomainEventPublisher

logger = logging.getLogger(__name__)

REVOCATION_REASON_USER_REQUEST = "user_request"
REVOCATION_REASON_USER_DELETED = "user_deleted"
REVOCATION_REASON_PASSWORD_CHANGED = "password_changed"  # noqa: S105 - an audit label, not a secret


class ExtensionRevocationRecordingService:
    """Publish and persist the audit trail for an extension-token revocation.

    Shared by the single and bulk revocations so both land in the audit log in
    the same shape.
    """

    @staticmethod
    def record(
        event_publisher: DomainEventPublisher,
        admin_event_repository: AdminEventRepository,
        user_id: UUID,
        token_id: UUID | None,
        reason: str,
        revoked_count: int,
    ) -> None:
        """Record that one or more credentials were revoked.

        Args:
            event_publisher: Where the domain event is published.
            admin_event_repository: Where the audit entry is appended.
            user_id: Owner of the revoked credentials.
            token_id: The revoked credential, or None for a bulk revocation.
            reason: What separates a deliberate revocation from a cascade
                (password change, account deletion) when the trail is read back.
            revoked_count: How many credentials this call actually revoked.
        """
        event = ExtensionTokenRevokedEvent(
            user_id=user_id,
            token_id=token_id,
            reason=reason,
            revoked_count=revoked_count,
        )
        event_publisher.publish(event)
        admin_event_repository.append_event(
            event_id=event.event_id,
            event_type=type(event).__name__,
            occurred_on=event.occurred_on,
            actor_user_id=user_id,
            event_data={
                "token_id": str(token_id) if token_id else None,
                "reason": reason,
                "revoked_count": revoked_count,
            },
        )
        logger.info(
            "Extension token(s) revoked",
            extra={"user_id": str(user_id), "reason": reason, "revoked_count": revoked_count},
        )
