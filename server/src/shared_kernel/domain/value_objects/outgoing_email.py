from dataclasses import dataclass


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str
