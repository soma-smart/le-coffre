from shared_kernel.domain.exceptions import EmailDeliveryError
from shared_kernel.domain.value_objects import OutgoingEmail


class FakeEmailGateway:
    def __init__(self):
        self.sent_emails: list[dict[str, str]] = []
        self.send_call_count = 0
        # Size of each send_bulk() call, in the order they were made — lets tests
        # assert a broadcast used one call for the whole batch, not one per recipient.
        self.send_bulk_call_sizes: list[int] = []
        self._should_fail = False

    def send(self, to: str, subject: str, body: str) -> None:
        self.send_call_count += 1
        if self._consume_failure():
            raise EmailDeliveryError("simulated SMTP failure")
        self.sent_emails.append({"to": to, "subject": subject, "body": body})

    def send_bulk(self, emails: list[OutgoingEmail]) -> list[tuple[str, EmailDeliveryError]]:
        self.send_bulk_call_sizes.append(len(emails))
        failures: list[tuple[str, EmailDeliveryError]] = []
        for email in emails:
            if self._consume_failure():
                failures.append((email.to, EmailDeliveryError("simulated SMTP failure")))
                continue
            self.sent_emails.append({"to": email.to, "subject": email.subject, "body": email.body})
        return failures

    def fail_next_send(self) -> None:
        """The next email attempted (via send() or within send_bulk()) fails once."""
        self._should_fail = True

    def _consume_failure(self) -> bool:
        if not self._should_fail:
            return False
        self._should_fail = False
        return True
