import logging
import smtplib
import ssl
from email.message import EmailMessage
from enum import Enum

from shared_kernel.application.gateways import EmailGateway
from shared_kernel.domain.exceptions import EmailDeliveryError
from shared_kernel.domain.value_objects import OutgoingEmail

logger = logging.getLogger(__name__)


class SmtpTlsMode(str, Enum):
    NONE = "none"
    IMPLICIT = "implicit"
    STARTTLS = "starttls"


class SmtpEmailGateway(EmailGateway):
    def __init__(
        self,
        host: str,
        port: int,
        from_address: str,
        username: str | None = None,
        password: str | None = None,
        tls_mode: SmtpTlsMode = SmtpTlsMode.NONE,
        timeout: float = 10,
        ssl_context: ssl.SSLContext | None = None,
    ):
        if (username is None) != (password is None):
            raise ValueError("SMTP username and password must be configured together")
        if username is not None and tls_mode == SmtpTlsMode.NONE:
            raise ValueError("SMTP credentials require TLS (implicit or starttls) to avoid sending them in cleartext")

        self._host = host
        self._port = port
        self._from_address = from_address
        self._username = username
        self._password = password
        self._tls_mode = tls_mode
        self._timeout = timeout
        self._ssl_context = ssl_context

    def send(self, to: str, subject: str, body: str) -> None:
        # Built before connecting: an invalid recipient or header fails right away,
        # not after a full connect + TLS + auth round trip.
        try:
            message = self._build_message(to, subject, body)
        except ValueError as error:
            raise EmailDeliveryError(str(error)) from error

        try:
            client = self._open_connection()
        except (smtplib.SMTPException, OSError) as error:
            raise EmailDeliveryError(str(error)) from error

        try:
            client.send_message(message)
        except (smtplib.SMTPException, OSError, ValueError) as error:
            self._close_connection(client)
            raise EmailDeliveryError(str(error)) from error
        self._close_connection(client)

    def send_bulk(self, emails: list[OutgoingEmail]) -> list[tuple[str, EmailDeliveryError]]:
        """Sends every email, reusing one connection instead of one per recipient —
        a broadcast to many opted-in recipients would otherwise be one handshake (and,
        with credentials, one auth round trip) per person. A failure sending one email
        is recorded and does not stop the rest. A failure to establish the connection
        itself is raised instead, since then nothing in the batch can be sent.

        Closing the connection is deliberately its own step, outside the try/except
        that turns a connection failure into EmailDeliveryError: smtplib's own
        context-manager __exit__ sends QUIT and raises if the relay's reply isn't
        exactly 221, which — if that happened here — would turn an already fully
        delivered batch into a reported total failure and lose `failures`. See
        _close_connection().
        """
        # Built before connecting, like send(): an invalid email is recorded as a
        # failure without a connection, and a batch with nothing valid opens none.
        failures: list[tuple[str, EmailDeliveryError]] = []
        messages: list[tuple[str, EmailMessage]] = []
        for email in emails:
            try:
                messages.append((email.to, self._build_message(email.to, email.subject, email.body)))
            except ValueError as error:
                failures.append((email.to, EmailDeliveryError(str(error))))
        if not messages:
            return failures

        try:
            client = self._open_connection()
        except (smtplib.SMTPException, OSError) as error:
            raise EmailDeliveryError(str(error)) from error

        try:
            for to, message in messages:
                try:
                    client.send_message(message)
                except (smtplib.SMTPException, OSError, ValueError) as error:
                    failures.append((to, EmailDeliveryError(str(error))))
        finally:
            self._close_connection(client)
        return failures

    def _open_connection(self) -> smtplib.SMTP:
        """Opens one authenticated connection to the relay, for one send or many.
        Raises smtplib.SMTPException/OSError on failure — nothing could be sent.

        Once the TCP (or TLS) connection is up, a failure in STARTTLS or in
        authentication must still close that socket before raising: unlike the
        stdlib's `with smtplib.SMTP(...) as client:`, a plain function has no
        __exit__ to fall back on, and a leaked half-open socket lingers until
        garbage collection — which, against a real server, can stall its own
        shutdown waiting on the orphaned connection.
        """
        if self._tls_mode == SmtpTlsMode.IMPLICIT:
            context = self._ssl_context or ssl.create_default_context()
            client: smtplib.SMTP = smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=context)
        else:
            client = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
            if self._tls_mode == SmtpTlsMode.STARTTLS:
                try:
                    client.starttls(context=self._ssl_context or ssl.create_default_context())
                except (smtplib.SMTPException, OSError):
                    client.close()
                    raise
        try:
            self._authenticate(client)
        except (smtplib.SMTPException, OSError):
            client.close()
            raise
        return client

    def _close_connection(self, client: smtplib.SMTP) -> None:
        """Best-effort QUIT, then close the socket regardless. Never raises: by the
        time this runs, every email already attempted has either sent or been
        recorded as a failure, and a relay misbehaving on QUIT must not turn that
        into a reported delivery failure (see send_bulk()'s docstring)."""
        try:
            client.quit()
        except (smtplib.SMTPException, OSError) as error:
            logger.warning("Failed to cleanly close the SMTP connection to %s:%s: %s", self._host, self._port, error)
        finally:
            client.close()

    def _authenticate(self, client: smtplib.SMTP) -> None:
        if self._username is not None and self._password is not None:
            client.login(self._username, self._password)

    def _build_message(self, to: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["From"] = self._from_address
        message["To"] = to
        if len(message["To"].addresses) != 1:
            raise ValueError("Recipient must be exactly one email address")
        message["Subject"] = subject
        message.set_content(body)
        return message
