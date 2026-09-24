from shared_kernel.domain.exceptions import EmailDeliveryError


class FakeEmailGateway:
    def __init__(self):
        self.sent_emails: list[dict[str, str]] = []
        self._should_fail = False

    def send(self, to: str, subject: str, body: str) -> None:
        if self._should_fail:
            raise EmailDeliveryError("simulated SMTP failure")
        self.sent_emails.append({"to": to, "subject": subject, "body": body})

    def fail_next_send(self) -> None:
        self._should_fail = True
