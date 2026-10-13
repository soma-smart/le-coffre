from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping
from uuid import UUID


class NotificationKind(Enum):
    """Every kind of email notification this context can send on request.

    Adding one means: a member here, its template in the notification catalog, and
    a subscriber that turns the triggering domain event into a `Notification`.
    Nothing about resolving the recipient or sending the email changes.
    """

    ONE_TIME_LINK_READ = "ONE_TIME_LINK_READ"
    ONE_TIME_LINK_EXPIRED = "ONE_TIME_LINK_EXPIRED"


@dataclass(frozen=True)
class Notification:
    """One email to send to one user: what happened, to whom, and the facts to mention.

    `params` holds plain strings (names, ISO timestamps) that the kind's template
    knows how to render; it never carries a secret.
    """

    kind: NotificationKind
    recipient_user_id: UUID
    params: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Frozen means immutable for real: a caller's dict must not change under us
        # while the notification waits in an executor queue.
        object.__setattr__(self, "params", MappingProxyType(dict(self.params)))
