from typing import Protocol


class EmailGateway(Protocol):
    def send(self, to: str, subject: str, body: str) -> None:
        """Sends a plain-text email to a single recipient"""
        ...
