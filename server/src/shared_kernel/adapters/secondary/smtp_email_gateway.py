import smtplib
import ssl
from email.message import EmailMessage
from enum import Enum

from shared_kernel.application.gateways import EmailGateway
from shared_kernel.domain.exceptions import EmailDeliveryError


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
        try:
            message = EmailMessage()
            message["From"] = self._from_address
            message["To"] = to
            message["Subject"] = subject
            message.set_content(body)

            if self._tls_mode == SmtpTlsMode.IMPLICIT:
                context = self._ssl_context or ssl.create_default_context()
                with smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=context) as client:
                    self._authenticate_and_send(client, message)
            else:
                with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
                    if self._tls_mode == SmtpTlsMode.STARTTLS:
                        client.starttls(context=self._ssl_context or ssl.create_default_context())
                    self._authenticate_and_send(client, message)
        except (smtplib.SMTPException, OSError, ValueError) as error:
            raise EmailDeliveryError(str(error)) from error

    def _authenticate_and_send(self, client: smtplib.SMTP, message: EmailMessage) -> None:
        if self._username is not None and self._password is not None:
            client.login(self._username, self._password)
        client.send_message(message)
