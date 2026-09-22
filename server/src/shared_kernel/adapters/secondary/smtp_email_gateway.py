import smtplib
import ssl
from email.message import EmailMessage

from shared_kernel.application.gateways import EmailGateway
from shared_kernel.domain.exceptions import EmailDeliveryError


class SmtpEmailGateway(EmailGateway):
    def __init__(
        self,
        host: str,
        port: int,
        from_address: str,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
        timeout: float = 10,
        ssl_context: ssl.SSLContext | None = None,
    ):
        self._host = host
        self._port = port
        self._from_address = from_address
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._timeout = timeout
        self._ssl_context = ssl_context

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._from_address
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            if self._use_tls:
                context = self._ssl_context or ssl.create_default_context()
                with smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=context) as client:
                    self._authenticate_and_send(client, message)
            else:
                with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as client:
                    self._authenticate_and_send(client, message)
        except (smtplib.SMTPException, OSError) as error:
            raise EmailDeliveryError(str(error)) from error

    def _authenticate_and_send(self, client: smtplib.SMTP, message: EmailMessage) -> None:
        if self._username:
            client.login(self._username, self._password or "")
        client.send_message(message)
