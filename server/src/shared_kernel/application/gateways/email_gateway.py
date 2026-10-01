from typing import Protocol

from shared_kernel.domain.exceptions import EmailDeliveryError
from shared_kernel.domain.value_objects import OutgoingEmail


class EmailGateway(Protocol):
    def send(self, to: str, subject: str, body: str) -> None:
        """Sends a plain-text email to a single recipient"""
        ...

    def send_bulk(self, emails: list[OutgoingEmail]) -> list[tuple[str, EmailDeliveryError]]:
        """Sends every email, reusing one connection to the relay rather than one per
        recipient. A failure sending one email does not stop the rest — failures come
        back as (to, error) pairs, in the order attempted, instead of being raised.
        A failure to even establish the connection is raised instead, since then
        nothing in the batch can be sent.
        """
        ...
