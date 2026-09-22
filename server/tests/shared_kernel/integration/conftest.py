import ipaddress
import socket
import ssl
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from aiosmtpd.controller import Controller
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from shared_kernel.adapters.secondary import InMemoryDomainEventPublisher
from shared_kernel.domain.entities import DomainEvent


class SampleTestEvent(DomainEvent):
    def __init__(self, event_id: UUID, occurred_on: datetime, data: str):
        super().__init__(event_id, occurred_on)
        self.data = data


class AnotherSampleTestEvent(DomainEvent):
    def __init__(self, event_id: UUID, occurred_on: datetime, value: int):
        super().__init__(event_id, occurred_on)
        self.value = value


@pytest.fixture
def event_publisher():
    return InMemoryDomainEventPublisher()


@pytest.fixture
def test_event():
    return SampleTestEvent(event_id=uuid4(), occurred_on=datetime.now(), data="test data")


@pytest.fixture
def another_test_event():
    return AnotherSampleTestEvent(event_id=uuid4(), occurred_on=datetime.now(), value=42)


class RecordingSmtpHandler:
    """Fake SMTP handler that records every accepted message for assertions."""

    def __init__(self):
        self.messages: list[dict] = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(
            {
                "mail_from": envelope.mail_from,
                "rcpt_tos": envelope.rcpt_tos,
                "content": envelope.content.decode("utf-8"),
            }
        )
        return "250 Message accepted for delivery"


@pytest.fixture
def recording_smtp_handler():
    return RecordingSmtpHandler()


def _free_tcp_port() -> int:
    """Reserves an OS-assigned free port. aiosmtpd's Controller cannot use port=0
    directly: its startup self-test connects to the literal port passed in, not the
    port the OS actually bound, so the port must be resolved up front instead."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture
def smtp_server(recording_smtp_handler):
    """Fake SMTP server with no authentication and no TLS."""
    controller = Controller(recording_smtp_handler, hostname="127.0.0.1", port=_free_tcp_port())
    controller.start()
    yield controller
    controller.stop()


@pytest.fixture
def smtp_server_requiring_auth(recording_smtp_handler):
    """Fake SMTP server that requires AUTH with a fixed username/password."""

    def auth_callback(mechanism: str, login: bytes, password: bytes) -> bool:
        return login == b"smtp-user" and password == b"smtp-password"

    controller = Controller(
        recording_smtp_handler,
        hostname="127.0.0.1",
        port=_free_tcp_port(),
        auth_required=True,
        auth_require_tls=False,
        auth_callback=auth_callback,
    )
    controller.start()
    yield controller
    controller.stop()


@pytest.fixture
def self_signed_certificate(tmp_path):
    """A self-signed cert/key pair (written to temp files) plus a client SSLContext trusting it."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    cert_path = tmp_path / "cert.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)

    server_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ssl_context.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))

    client_ssl_context = ssl.create_default_context(cadata=cert_pem.decode())

    return server_ssl_context, client_ssl_context


@pytest.fixture
def smtp_server_with_tls(recording_smtp_handler, self_signed_certificate):
    """Fake SMTP server listening over implicit TLS (SMTPS)."""
    server_ssl_context, _ = self_signed_certificate
    controller = Controller(
        recording_smtp_handler,
        hostname="127.0.0.1",
        port=_free_tcp_port(),
        ssl_context=server_ssl_context,
    )
    controller.start()
    yield controller
    controller.stop()


@pytest.fixture
def unreachable_smtp_port():
    """A TCP port with nothing listening on it, to simulate an unreachable SMTP server."""
    return _free_tcp_port()
