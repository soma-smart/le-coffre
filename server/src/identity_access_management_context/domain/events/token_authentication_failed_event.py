from datetime import datetime
from uuid import UUID, uuid4

from identity_access_management_context.domain.exceptions import TokenAuthenticationFailureReason
from shared_kernel.domain.entities import DomainEvent
from shared_kernel.domain.value_objects import EventPriority


class TokenAuthenticationFailedEvent(DomainEvent):
    """A request presented a token that was refused.

    About the credential, not its holder: most failures (missing, malformed,
    unknown token) happen before any principal is known, and the kind of
    credential says nothing about the kind of principal anyway.

    A token has no lockout to fall back on, unlike a password login: this trail
    is what shows someone trying a leaked or guessed token.

    Never carries the token, nor its hash: the hash is checkable against a
    candidate token, so a leaked event row would help confirm a guess.
    """

    def __init__(
        self,
        reason: TokenAuthenticationFailureReason,
        client_ip: str,
        occurred_on: datetime,
        principal_id: UUID | None = None,
        event_id: UUID | None = None,
    ):
        super().__init__(
            event_id=event_id or uuid4(),
            occurred_on=occurred_on,
            priority=EventPriority.HIGH,
        )
        self.reason = reason
        self.client_ip = client_ip
        self.principal_id = principal_id
        """The principal holding the token, when the token itself was valid."""

    @property
    def event_data(self) -> dict[str, str]:
        data = {"reason": self.reason.value, "client_ip": self.client_ip}
        if self.principal_id is not None:
            data["principal_id"] = str(self.principal_id)
        return data
