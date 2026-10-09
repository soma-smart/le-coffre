from datetime import datetime
from uuid import UUID, uuid4

from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class ExtensionTokenRevokedEvent(DomainEvent):
    """A browser-extension credential was revoked.

    `reason` distinguishes a deliberate revocation from a cascade (password
    change, account deletion), which is the difference between "the user tidied
    up" and "access was cut for them" when reading the audit trail back.
    """

    def __init__(
        self,
        user_id: UUID,
        token_id: UUID | None,
        reason: str,
        revoked_count: int = 1,
        event_id: UUID | None = None,
        occurred_on: datetime | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on or datetime.now(),
            priority=EventPriority.HIGH,
        )
        self.user_id = user_id
        self.token_id = token_id
        self.reason = reason
        self.revoked_count = revoked_count
